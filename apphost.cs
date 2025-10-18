#:sdk Aspire.AppHost.Sdk@13.0.0-preview.1.25517.6
#:package Aspire.Hosting.NodeJs@13.0.0-preview.1.25517.6
#:package Aspire.Hosting.Python@13.0.0-preview.1.25517.6
#:package CommunityToolkit.Aspire.Hosting.NodeJS.Extensions@9.8.0
#:package dotenv.net@4.0.0

using dotenv.net;

var envVars = DotEnv.Read();

var builder = DistributedApplication.CreateBuilder(args);
#pragma warning disable ASPIREHOSTINGPYTHON001

var financeMcp = builder.AddPythonModule("finance-mcp", "./app/mcp/", "github_shop_mcp.finance_server")
    .WithUvEnvironment()
    .WithHttpEndpoint(env: "PORT")
    .WithEnvironment("OTEL_PYTHON_CONFIGURATOR", "configurator")
    .WithEnvironment("OTEL_PYTHON_DISTRO", "not_azure")
    .WithExternalHttpEndpoints();

var supplierMcp = builder.AddPythonModule("supplier-mcp", "./app/mcp/", "github_shop_mcp.supplier_server")
    .WithUvEnvironment()
    .WithHttpEndpoint(env: "PORT")
    .WithEnvironment("OTEL_PYTHON_CONFIGURATOR", "configurator")
    .WithEnvironment("OTEL_PYTHON_DISTRO", "not_azure")
    .WithExternalHttpEndpoints();

var apiService = builder.AddPythonModule("api", "./app/api/", "uvicorn")
    .WithArgs("github_shop_api.app:app", "--reload")
    .WithUvEnvironment()
    .WithHttpEndpoint(env: "UVICORN_PORT")
    .WithHttpHealthCheck("/health")
    .WithEnvironment("FINANCE_MCP_HTTP", financeMcp.GetEndpoint("http") + "/mcp")
    .WithEnvironment("SUPPLIER_MCP_HTTP", supplierMcp.GetEndpoint("http") + "/mcp")
    // OpenAI settings
    .WithEnvironment("AZURE_OPENAI_ENDPOINT_GPT5", envVars["AZURE_OPENAI_ENDPOINT_GPT5"])
    .WithEnvironment("AZURE_OPENAI_API_KEY_GPT5", envVars["AZURE_OPENAI_API_KEY_GPT5"])
    .WithEnvironment("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5", envVars["AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5"])
    .WithEnvironment("AZURE_OPENAI_ENDPOINT_VERSION_GPT5", envVars["AZURE_OPENAI_ENDPOINT_VERSION_GPT5"])
    // TODO: turn this off in production
    .WithEnvironment("OTEL_PYTHON_CONFIGURATOR", "configurator")
    .WithEnvironment("OTEL_PYTHON_DISTRO", "not_azure")
    .WithExternalHttpEndpoints();


builder.AddViteApp("frontend", "./frontend")
    .WithNpmPackageInstallation()
    .WithReference(apiService)
    .WaitFor(apiService);

builder.Build().Run();
