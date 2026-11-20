"""Render REST API client for automated deployment."""
import requests
from typing import Optional

RENDER_API_BASE = "https://api.render.com/v1"


class RenderAPIError(Exception):
    pass


class RenderClient:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip()
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> dict | list:
        url = f"{RENDER_API_BASE}{endpoint}"
        try:
            resp = requests.request(method, url, headers=self.headers, timeout=30, **kwargs)
            if resp.status_code == 204 or not resp.text or not resp.text.strip():
                return {}
            if not resp.ok:
                err_msg = resp.text.strip()
                try:
                    err_json = resp.json()
                    err_msg = err_json.get("message") or err_json.get("error") or err_msg
                except Exception:
                    pass
                raise RenderAPIError(f"Render API error ({resp.status_code}): {err_msg}")
            try:
                return resp.json()
            except Exception:
                return {"text": resp.text.strip()}
        except RenderAPIError:
            raise
        except requests.RequestException as exc:
            raise RenderAPIError(f"Network error communicating with Render: {str(exc)}") from exc
        except Exception as exc:
            raise RenderAPIError(f"Error communicating with Render: {str(exc)}") from exc

    def get_owners(self) -> list:
        """Fetch list of user/team accounts associated with the API key."""
        return self._request("GET", "/owners")

    def list_services(self) -> list:
        """Fetch list of deployed services."""
        res = self._request("GET", "/services?limit=50")
        if isinstance(res, list):
            return res
        if isinstance(res, dict) and "services" in res:
            return res["services"]
        return []

    def find_service_by_name(self, name: str) -> Optional[dict]:
        services = self.list_services()
        for item in services:
            service = item.get("service", item) if isinstance(item, dict) else {}
            if service.get("name") == name:
                return service
        return None

    def create_web_service(
        self,
        name: str,
        owner_id: str,
        repo_url: str,
        branch: str = "main",
        region: str = "singapore",
        plan: str = "free",
        env_vars: list[dict] = None,
    ) -> dict:
        """Create a new Web Service on Render."""
        payload = {
            "type": "web_service",
            "name": name,
            "ownerId": owner_id,
            "repo": repo_url,
            "branch": branch,
            "autoDeploy": "yes",
            "serviceDetails": {
                "env": "python",
                "plan": plan,
                "region": region,
                "envSpecificDetails": {
                    "buildCommand": "pip install -r requirements.txt",
                    "startCommand": "python app/production.py --host 0.0.0.0 --port $PORT",
                },
            },
            "envVars": env_vars or [],
        }
        return self._request("POST", "/services", json=payload)

    def update_env_vars(self, service_id: str, env_vars: list[dict]) -> dict:
        """Update environment variables for an existing service."""
        return self._request("PUT", f"/services/{service_id}/env-vars", json=env_vars)

    def trigger_deploy(self, service_id: str, clear_cache: bool = False, commit_id: str = None) -> dict:
        """Trigger a new deployment for a service."""
        payload = {"clearCache": "clear" if clear_cache else "do_not_clear"}
        if commit_id:
            payload["commitId"] = commit_id.strip()
        return self._request("POST", f"/services/{service_id}/deploys", json=payload)

    def get_deploy_status(self, service_id: str, deploy_id: str) -> dict:
        """Get the status of a specific deployment."""
        return self._request("GET", f"/services/{service_id}/deploys/{deploy_id}")

    def get_service(self, service_id: str) -> dict:
        """Fetch full service details."""
        return self._request("GET", f"/services/{service_id}")
