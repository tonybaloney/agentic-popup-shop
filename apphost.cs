#:sdk Aspire.AppHost.Sdk@13.0.0-preview.1.25520.1
#:package Aspire.Hosting.NodeJs@13.0.0-preview.1.25520.1
#:package Aspire.Hosting.Python@13.0.0-preview.1.25520.1
#:package CommunityToolkit.Aspire.Hosting.NodeJS.Extensions@9.8.0
#:package dotenv.net@4.0.0

using dotenv.net;

var envVars = DotEnv.Read();

var builder = DistributedApplication.CreateBuilder(args);
#pragma warning disable ASPIREHOSTINGPYTHON001

var financeMcp = builder.AddPythonModule("finance-mcp", "./app/mcp/", "github_shop_mcp.finance_server")
    .WithUvEnvironment()
    .WithHttpEndpoint(env: "PORT")
    .WithExternalHttpEndpoints();

if (envVars.TryGetValue("APPLICATIONINSIGHTS_CONNECTION_STRING", out var appInsightsConnectionString))
{
    financeMcp = financeMcp.WithEnvironment("APPLICATIONINSIGHTS_CONNECTION_STRING", appInsightsConnectionString);
} else {
    financeMcp = financeMcp.WithEnvironment("OTEL_PYTHON_CONFIGURATOR", "configurator")
                           .WithEnvironment("OTEL_PYTHON_DISTRO", "not_azure");
}

var supplierMcp = builder.AddPythonModule("supplier-mcp", "./app/mcp/", "github_shop_mcp.supplier_server")
    .WithUvEnvironment()
    .WithHttpEndpoint(env: "PORT")
    .WithExternalHttpEndpoints();

if (! string.IsNullOrEmpty(appInsightsConnectionString))
{
    supplierMcp = supplierMcp.WithEnvironment("APPLICATIONINSIGHTS_CONNECTION_STRING", appInsightsConnectionString);
} else {
    supplierMcp = supplierMcp.WithEnvironment("OTEL_PYTHON_CONFIGURATOR", "configurator")
                             .WithEnvironment("OTEL_PYTHON_DISTRO", "not_azure");
}

var apiService = builder.AddPythonModule("api", "./app/api/", "uvicorn")
    .WithArgs("github_shop_api.app:app", "--reload")
    .WithUvEnvironment()
    .WithHttpEndpoint(env: "UVICORN_PORT")
    .WithHttpHealthCheck("/health")
    .WithEnvironment("FINANCE_MCP_HTTP", financeMcp.GetEndpoint("http"))
    .WithEnvironment("SUPPLIER_MCP_HTTP", supplierMcp.GetEndpoint("http"))
    // OpenAI settings
    .WithEnvironment("AZURE_OPENAI_ENDPOINT_GPT5", envVars["AZURE_OPENAI_ENDPOINT_GPT5"])
    .WithEnvironment("AZURE_OPENAI_API_KEY_GPT5", envVars["AZURE_OPENAI_API_KEY_GPT5"])
    .WithEnvironment("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5", envVars["AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5"])
    .WithEnvironment("AZURE_OPENAI_ENDPOINT_VERSION_GPT5", envVars["AZURE_OPENAI_ENDPOINT_VERSION_GPT5"])
    .WithExternalHttpEndpoints();

if (! string.IsNullOrEmpty(appInsightsConnectionString))
{
    apiService = apiService.WithEnvironment("APPLICATIONINSIGHTS_CONNECTION_STRING", appInsightsConnectionString);
} else {
    apiService = apiService.WithEnvironment("OTEL_PYTHON_CONFIGURATOR", "configurator")
                           .WithEnvironment("OTEL_PYTHON_DISTRO", "not_azure");
}

builder.AddViteApp("frontend", "./frontend")
    .WithNpmPackageInstallation()
    .WithReference(apiService)
    .WaitFor(apiService);

builder.Build().Run();
