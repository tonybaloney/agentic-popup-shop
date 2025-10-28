#:sdk Aspire.AppHost.Sdk@13.0.0-preview.1.25523.9
#:package Aspire.Hosting.NodeJs@13.0.0-preview.1.25523.9
#:package Aspire.Hosting.Python@13.0.0-preview.1.25523.9
#:package dotenv.net@4.0.0

using dotenv.net;

var envVars = DotEnv.Read();

var builder = DistributedApplication.CreateBuilder(args);
#pragma warning disable ASPIREHOSTINGPYTHON001

envVars.TryGetValue("APPLICATIONINSIGHTS_CONNECTION_STRING", out string? appInsightsConnectionString);

var financeMcp = builder.AddPythonModule("finance-mcp", "./app/mcp/", "zava_shop_mcp.finance_server")
    .WithUvEnvironment()
    .WithHttpEndpoint(env: "PORT")
    .WithHttpHealthCheck("/health")
    .WithEnvironment("OTEL_PYTHON_EXCLUDED_URLS", "/health")
    .WithTracing(appInsightsConnectionString)
    .WithEnvironment("DEV_GUEST_TOKEN", envVars["DEV_GUEST_TOKEN"])
    .WithExternalHttpEndpoints();

var supplierMcp = builder.AddPythonModule("supplier-mcp", "./app/mcp/", "zava_shop_mcp.supplier_server")
    .WithUvEnvironment()
    .WithHttpEndpoint(env: "PORT")
    .WithHttpHealthCheck("/health")
    .WithEnvironment("OTEL_PYTHON_EXCLUDED_URLS", "/health")
    .WithTracing(appInsightsConnectionString)
    .WithEnvironment("DEV_GUEST_TOKEN", envVars["DEV_GUEST_TOKEN"])
    .WithExternalHttpEndpoints();

var agentDev = builder.AddPythonModule("agent-dev", "./app/agents/", "zava_shop_agents")
    .WithUvEnvironment()
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
    .WithTracing(appInsightsConnectionString)
    .WithEnvironment("DEV_GUEST_TOKEN", envVars["DEV_GUEST_TOKEN"])
    .WithExternalHttpEndpoints();


var apiService = builder.AddPythonModule("api", "./app/api/", "uvicorn")
    .WithArgs("zava_shop_api.app:app", "--reload")
    .WithUvEnvironment()
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
    .WithTracing(appInsightsConnectionString)
    .WithEnvironment("DEV_GUEST_TOKEN", envVars["DEV_GUEST_TOKEN"])
    .WithExternalHttpEndpoints();

builder.AddViteApp("frontend", "./frontend")
    .WithNpmPackageManager()
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