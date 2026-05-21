import argparse
import ast
import os
import sys
import requests
from pathlib import Path
from azure.identity import ClientSecretCredential
from fabric_cicd import (
    FabricWorkspace,
    publish_all_items,
    unpublish_all_orphan_items,
    change_log_level,
)


def get_workspace_id(workspace_name, token_credential):
    resource = "https://api.fabric.microsoft.com/"
    scope    = f"{resource}.default"
    token    = token_credential.get_token(scope)
    url      = "https://api.fabric.microsoft.com/v1/workspaces"
    headers  = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type":  "application/json",
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ConnectionError(
            f"Failed to list workspaces. HTTP {response.status_code}: {response.text}"
        )
    for ws in response.json().get("value", []):
        if ws.get("displayName") == workspace_name:
            print(f"  Resolved '{workspace_name}' to {ws['id']}")
            return ws["id"]
    raise ValueError(
        f"Workspace '{workspace_name}' not found. "
        f"Check SP has Member/Admin access to this workspace."
    )


def get_workspace_name(environment):
    env_var = f"{environment.upper()}_WORKSPACE_NAME"
    name    = os.environ.get(env_var)
    if not name:
        raise EnvironmentError(
            f"Environment variable '{env_var}' is not set. "
            f"Add it as a GitHub Variable in repo settings."
        )
    return name


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Fabric items via fabric-cicd"
    )
    parser.add_argument("--tenant-id",      required=True)
    parser.add_argument("--client-id",      required=True)
    parser.add_argument("--client-secret",  required=True)
    parser.add_argument(
        "--environment",
        required=True,
        choices=["dev", "test", "prod"]
    )
    parser.add_argument(
        "--items-in-scope",
        required=False,
        default='["Notebook","DataPipeline","Lakehouse","VariableLibrary","Environment"]'
    )
    args = parser.parse_args()

    try:
        item_types = ast.literal_eval(args.items_in_scope)
        if not isinstance(item_types, list):
            raise ValueError
    except (ValueError, SyntaxError):
        print("ERROR: --items-in-scope must be a valid list string.")
        sys.exit(1)

    change_log_level("DEBUG")

    environment          = args.environment
    repository_directory = Path(__file__).parent.parent / "workspace"

    print("=" * 50)
    print(f"  Target environment : {environment.upper()}")
    print(f"  Items in scope     : {item_types}")
    print(f"  Repository path    : {repository_directory}")
    print("=" * 50)

    print("\n[1/4] Authenticating as Service Principal...")
    token_credential = ClientSecretCredential(
        tenant_id     = args.tenant_id,
        client_id     = args.client_id,
        client_secret = args.client_secret,
    )

    print("\n[2/4] Resolving workspace ID...")
    workspace_name = get_workspace_name(environment)
    print(f"  Workspace name: {workspace_name}")
    workspace_id = get_workspace_id(workspace_name, token_credential)

    print("\n[3/4] Initialising deployment context...")
    target_workspace = FabricWorkspace(
        workspace_id         = workspace_id,
        environment          = environment,
        repository_directory = str(repository_directory),
        item_type_in_scope   = item_types,
        token_credential     = token_credential,
    )

    print("\n[4/4] Deploying items...")
    publish_all_items(target_workspace)
    unpublish_all_orphan_items(target_workspace)

    print("\n✅ Deployment complete.")


if __name__ == "__main__":
    main()
