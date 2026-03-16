#:sdk Aspire.AppHost.Sdk@13.3.0-preview.1.26156.8
#:package Aspire.Hosting.JavaScript@13.3.0-preview.1.26156.8
#:package Aspire.Hosting.Python@13.3.0-preview.1.26156.8
#:package dotenv.net@4.0.0

using dotenv.net;

var envVars = DotEnv.Read();

var builder = DistributedApplication.CreateBuilder(args);
#pragma warning disable ASPIREHOSTINGPYTHON001

var adminPassword = builder.AddParameter("kcAdminPassword", secret: true);

envVars.TryGetValue("APPLICATIONINSIGHTS_CONNECTION_STRING", out string? appInsightsConnectionString);

var authServer = builder.AddDockerfile("keycloak", "./auth/")
    .WithHttpEndpoint(env: "PORT", targetPort: 8080)
    .WithHttpHealthCheck("/health")
    .WithEnvironment("KC_BOOTSTRAP_ADMIN_USERNAME", "admin")
    .WithEnvironment("KC_BOOTSTRAP_ADMIN_PASSWORD", adminPassword)
    .WithOtlpExporter()
    .WithExternalHttpEndpoints();

var financeMcp = builder.AddPythonModule("finance-mcp", "./app/mcp/", "zava_shop_mcp.finance_server")
    .WithUv()
    .WithHttpEndpoint(env: "PORT")
    .WithEndpoint("http", e =>
    {
        e.Port = 28001;
    })
    .WithHttpHealthCheck("/health")
    .WithEnvironment("OTEL_PYTHON_EXCLUDED_URLS", "/health")
    .WithEnvironment("KEYCLOAK_REALM_URL", $"{authServer.GetEndpoint("http")}/realms/zava")
    .WithTracing(appInsightsConnectionString)
    .WithExternalHttpEndpoints();

var supplierMcp = builder.AddPythonModule("supplier-mcp", "./app/mcp/", "zava_shop_mcp.supplier_server")
    .WithUv()
    .WithHttpEndpoint(env: "PORT")
    .WithEndpoint("http", e =>
    {
        e.Port = 28002;
    })
    .WithHttpHealthCheck("/health")
    .WithEnvironment("OTEL_PYTHON_EXCLUDED_URLS", "/health")
    .WithEnvironment("KEYCLOAK_REALM_URL", $"{authServer.GetEndpoint("http")}/realms/zava")
    .WithTracing(appInsightsConnectionString)
    .WithExternalHttpEndpoints();

var customerMcp = builder.AddPythonModule("customer-mcp", "./app/mcp/", "zava_shop_mcp.customer_server")
    .WithUv()
    .WithHttpEndpoint(env: "PORT")
    .WithEndpoint("http", e =>
    {
        e.Port = 28003;
    })
    .WithHttpHealthCheck("/health")
    .WithEnvironment("OTEL_PYTHON_EXCLUDED_URLS", "/health")
    .WithEnvironment("KEYCLOAK_REALM_URL", $"{authServer.GetEndpoint("http")}/realms/zava")
    .WithTracing(appInsightsConnectionString)
    .WithExternalHttpEndpoints();

var agentDev = builder.AddPythonModule("agent-dev", "./app/agents/", "zava_shop_agents")
    .WithUv(args: ["sync", "--prerelease=allow", "--link-mode=copy"])
    .WithHttpEndpoint(env: "PORT")
    .WithHttpHealthCheck("/health")
    .WithEnvironment("OTEL_PYTHON_EXCLUDED_URLS", "/health")
    .WithEnvironment("FINANCE_MCP_HTTP", financeMcp.GetEndpoint("http"))
    .WithEnvironment("SUPPLIER_MCP_HTTP", supplierMcp.GetEndpoint("http"))
    // Agent SDK
    .WithEnvironment("AZURE_AI_PROJECT_ENDPOINT", envVars["AZURE_AI_PROJECT_ENDPOINT"])
    .WithEnvironment("AZURE_AI_PROJECT_AGENT_ID", envVars["AZURE_AI_PROJECT_AGENT_ID"])
    .WithEnvironment("AZURE_AI_MODEL_DEPLOYMENT_NAME", envVars["AZURE_AI_MODEL_DEPLOYMENT_NAME"])
    // Insights search
    .WithEnvironment("OPENWEATHER_API_KEY", envVars["OPENWEATHER_API_KEY"])
    .WithEnvironment("BING_CUSTOM_CONNECTION_ID", envVars["BING_CUSTOM_CONNECTION_ID"])
    .WithEnvironment("BING_CUSTOM_INSTANCE_NAME", envVars["BING_CUSTOM_INSTANCE_NAME"])
    .WithEnvironment("BING_CUSTOM_CONNECTION_NAME", envVars["BING_CUSTOM_CONNECTION_NAME"])
    .WithEnvironment("BING_API_KEY", envVars["BING_API_KEY"])

    .WithTracing(appInsightsConnectionString)
    .WithExternalHttpEndpoints();


var apiService = builder.AddPythonModule("api", "./app/api/", "uvicorn")
    .WithArgs("zava_shop_api.app:app")
    .WithUv(args: ["sync", "--prerelease=allow", "--link-mode=copy"])
    .WithCertificateTrustScope(CertificateTrustScope.System)
    .WithHttpEndpoint(env: "UVICORN_PORT")
    .WithHttpHealthCheck("/health")
    .WithEnvironment("OTEL_PYTHON_EXCLUDED_URLS", "/health")
    .WithEnvironment("FINANCE_MCP_HTTP", financeMcp.GetEndpoint("http"))
    .WithEnvironment("SUPPLIER_MCP_HTTP", supplierMcp.GetEndpoint("http"))
    // Auth
    .WithEnvironment("KEYCLOAK_SERVER_URL", $"{authServer.GetEndpoint("http")}/auth")
    .WithEnvironment("KEYCLOAK_REALM", "zava")
    .WithEnvironment("KEYCLOAK_CLIENT_ID", "zava-api")
    .WithEnvironment("KEYCLOAK_CLIENT_SECRET", envVars["ZAVA_API_CLIENT_SECRET"])
    // Agent SDK
    .WithEnvironment("AZURE_AI_PROJECT_ENDPOINT", envVars["AZURE_AI_PROJECT_ENDPOINT"])
    .WithEnvironment("AZURE_AI_PROJECT_AGENT_ID", envVars["AZURE_AI_PROJECT_AGENT_ID"])
    // Insights search
    .WithEnvironment("OPENWEATHER_API_KEY", envVars["OPENWEATHER_API_KEY"])
    .WithEnvironment("BING_CUSTOM_CONNECTION_ID", envVars["BING_CUSTOM_CONNECTION_ID"])
    .WithEnvironment("BING_CUSTOM_INSTANCE_NAME", envVars["BING_CUSTOM_INSTANCE_NAME"])
    .WithEnvironment("BING_CUSTOM_CONNECTION_NAME", envVars["BING_CUSTOM_CONNECTION_NAME"])
    .WithEnvironment("BING_API_KEY", envVars["BING_API_KEY"])
    // Extra
    .WithTracing(appInsightsConnectionString)    // TODO: Review this setting
    .WithExternalHttpEndpoints();

builder.AddViteApp("frontend", "./frontend")
    .WithNpm(install: true)
    .WithEnvironment("VITE_CHATKIT_DOMAIN_KEY", envVars["VITE_CHATKIT_DOMAIN_KEY"])
    .WithReference(apiService)
    .WithEndpoint("http", e =>
    {
        e.Port = 28000;
    })
    .WaitFor(apiService);

builder.Build().Run();

public static class TracingExtensions {
    
    public static IResourceBuilder<T> WithTracing<T>(this IResourceBuilder<T> builder, string? appInsightsConnectionString) where T : Aspire.Hosting.ApplicationModel.IResourceWithEnvironment
    {
        if (! string.IsNullOrEmpty(appInsightsConnectionString))
        {
            return builder.WithEnvironment("APPLICATIONINSIGHTS_CONNECTION_STRING", appInsightsConnectionString);
        }
        return builder.WithEnvironment("OTEL_PYTHON_CONFIGURATOR", "configurator")
                            .WithEnvironment("OTEL_PYTHON_DISTRO", "not_azure");
    }
}