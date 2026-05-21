import argparse, ast, os, sys, requests
from azure.identity import ClientSecretCredential
from fabric_cicd import FabricWorkspace, publish_all_items, 
                        unpublish_all_orphan_items, change_log_level

def get_workspace_id(workspace_name, token_credential):
    token = token_credential.get_token("https://api.fabric.microsoft.com/.default")

    response = requests.get("https://api.fabric.microsoft.com/v1/workspaces",
                            headers={"Authorization": f"Bearer {token.token}"})

    for ws in response.json()["value"]:
        if ws["displayName"] == workspace_name:
            return ws["id"]

    raise ValueError(f"Workspace '{workspace_name}' not found.")

def get_workspace_name(environment):
    env_var = f"{environment.upper()}_WORKSPACE_NAME"
    name = os.environ.get(env_var)
    return name

parser.add_argument("--tenant-id",     required=True)
parser.add_argument("--client-id",     required=True)
parser.add_argument("--client-secret", required=True)
parser.add_argument("--environment",   required=True, choices=["dev","test","prod"])
parser.add_argument("--items-in-scope", required=False, default='["Notebook",...]')

token_credential = ClientSecretCredential(
    tenant_id     = args.tenant_id,
    client_id     = args.client_id,
    client_secret = args.client_secret,
)

workspace_name = get_workspace_name(environment)   # reads AIW-TEST from env var
workspace_id   = get_workspace_id(workspace_name, token_credential)  # calls Fabric API

target_workspace = FabricWorkspace(
    workspace_id         = workspace_id,
    environment          = environment,
    repository_directory = str(repository_directory),  # points to workspace/ folder
    item_type_in_scope   = item_types,
    token_credential     = token_credential,
)

publish_all_items(target_workspace)          # push items from repo → workspace
unpublish_all_orphan_items(target_workspace) # remove items in workspace not in repo

