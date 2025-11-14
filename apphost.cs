#:sdk Aspire.AppHost.Sdk@13.0.0
#:package Aspire.Hosting.JavaScript@13.0.0
#:package Aspire.Hosting.Python@13.0.0
#:package dotenv.net@4.0.0

using dotenv.net;

var envVars = DotEnv.Read();

var builder = DistributedApplication.CreateBuilder(args);
#pragma warning disable ASPIREHOSTINGPYTHON001

envVars.TryGetValue("APPLICATIONINSIGHTS_CONNECTION_STRING", out string? appInsightsConnectionString);

var financeMcp = builder.AddPythonModule("finance-mcp", "./app/mcp/", "zava_shop_mcp.finance_server")
    .WithUv()
    .WithHttpEndpoint(env: "PORT")
    .WithEndpoint("http", e =>
    {
        e.Port = 28001;
    })
    .WithHttpHealthCheck("/health")
    .WithEnvironment("OTEL_PYTHON_EXCLUDED_URLS", "/health")
    .WithTracing(appInsightsConnectionString)
    .WithEnvironment("DEV_GUEST_TOKEN", envVars["DEV_GUEST_TOKEN"])
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
    .WithTracing(appInsightsConnectionString)
    .WithEnvironment("DEV_GUEST_TOKEN", envVars["DEV_GUEST_TOKEN"])
    .WithExternalHttpEndpoints();

var agentDev = builder.AddPythonModule("agent-dev", "./app/agents/", "zava_shop_agents")
    .WithUv(args: ["sync", "--prerelease=allow", "--link-mode=copy"])
    .WithHttpEndpoint(env: "PORT")
    .WithHttpHealthCheck("/health")
    .WithEnvironment("OTEL_PYTHON_EXCLUDED_URLS", "/health")
    .WithEnvironment("FINANCE_MCP_HTTP", financeMcp.GetEndpoint("http"))
    .WithEnvironment("SUPPLIER_MCP_HTTP", supplierMcp.GetEndpoint("http"))
    // OpenAI settings
    .WithEnvironment("AZURE_OPENAI_ENDPOINT_GPT5", envVars["AZURE_OPENAI_ENDPOINT_GPT5"])
    .WithEnvironment("AZURE_OPENAI_API_KEY_GPT5", envVars["AZURE_OPENAI_API_KEY_GPT5"])
    .WithEnvironment("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5", envVars["AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5"])
    .WithEnvironment("AZURE_OPENAI_ENDPOINT_VERSION_GPT5", envVars["AZURE_OPENAI_ENDPOINT_VERSION_GPT5"])
    // Agent SDK
    .WithEnvironment("AZURE_AI_PROJECT_ENDPOINT", envVars["AZURE_AI_PROJECT_ENDPOINT"])
    .WithEnvironment("AZURE_AI_PROJECT_API_KEY", envVars["AZURE_AI_PROJECT_API_KEY"])
    .WithEnvironment("AZURE_AI_PROJECT_AGENT_VERSION", envVars["AZURE_AI_PROJECT_AGENT_VERSION"])
    .WithEnvironment("AZURE_AI_PROJECT_AGENT_ID", envVars["AZURE_AI_PROJECT_AGENT_ID"])
    // Insights search
    .WithEnvironment("OPENWEATHER_API_KEY", envVars["OPENWEATHER_API_KEY"])
    .WithEnvironment("BING_CUSTOM_CONNECTION_ID", envVars["BING_CUSTOM_CONNECTION_ID"])
    .WithEnvironment("BING_CUSTOM_INSTANCE_NAME", envVars["BING_CUSTOM_INSTANCE_NAME"])
    .WithEnvironment("BING_CUSTOM_CONNECTION_NAME", envVars["BING_CUSTOM_CONNECTION_NAME"])
    .WithEnvironment("BING_API_KEY", envVars["BING_API_KEY"])

    .WithTracing(appInsightsConnectionString)
    .WithEnvironment("DEV_GUEST_TOKEN", envVars["DEV_GUEST_TOKEN"])
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
    // OpenAI settings
    .WithEnvironment("AZURE_OPENAI_ENDPOINT_GPT5", envVars["AZURE_OPENAI_ENDPOINT_GPT5"])
    .WithEnvironment("AZURE_OPENAI_API_KEY_GPT5", envVars["AZURE_OPENAI_API_KEY_GPT5"])
    .WithEnvironment("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5", envVars["AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5"])
    .WithEnvironment("AZURE_OPENAI_ENDPOINT_VERSION_GPT5", envVars["AZURE_OPENAI_ENDPOINT_VERSION_GPT5"])
    // Agent SDK
    .WithEnvironment("AZURE_AI_PROJECT_ENDPOINT", envVars["AZURE_AI_PROJECT_ENDPOINT"])
    .WithEnvironment("AZURE_AI_PROJECT_API_KEY", envVars["AZURE_AI_PROJECT_API_KEY"])
    .WithEnvironment("AZURE_AI_PROJECT_AGENT_VERSION", envVars["AZURE_AI_PROJECT_AGENT_VERSION"])
    .WithEnvironment("AZURE_AI_PROJECT_AGENT_ID", envVars["AZURE_AI_PROJECT_AGENT_ID"])
    // Insights search
    .WithEnvironment("OPENWEATHER_API_KEY", envVars["OPENWEATHER_API_KEY"])
    .WithEnvironment("BING_CUSTOM_CONNECTION_ID", envVars["BING_CUSTOM_CONNECTION_ID"])
    .WithEnvironment("BING_CUSTOM_INSTANCE_NAME", envVars["BING_CUSTOM_INSTANCE_NAME"])
    .WithEnvironment("BING_CUSTOM_CONNECTION_NAME", envVars["BING_CUSTOM_CONNECTION_NAME"])
    .WithEnvironment("BING_API_KEY", envVars["BING_API_KEY"])
    // Extra
    .WithTracing(appInsightsConnectionString)
    .WithEnvironment("DEV_GUEST_TOKEN", envVars["DEV_GUEST_TOKEN"])
    .WithExternalHttpEndpoints();

builder.AddViteApp("frontend", "./frontend")
    .WithNpm(install: true)
    .WithEnvironment("VITE_CHATKIT_DOMAIN_KEY", envVars["VITE_CHATKIT_DOMAIN_KEY"])
    .WithReference(apiService)
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