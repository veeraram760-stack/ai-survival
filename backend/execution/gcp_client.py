from google.cloud import aiplatform_v1
from google.oauth2 import service_account
from typing import Optional, Dict, Any
import os


class VertexAIClient:
    def __init__(self, project_id: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        self.credentials = None
        self._client = None

    def _get_client(self):
        if self._client is None:
            key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if key_path and os.path.exists(key_path):
                self.credentials = service_account.Credentials.from_service_account_file(key_path)
            self._client = aiplatform_v1.PredictionServiceClient(credentials=self.credentials)
        return self._client

    async def generate_text(self, prompt: str, model: str = "gemini-1.5-flash") -> Dict[str, Any]:
        try:
            client = self._get_client()
            endpoint = f"projects/{self.project_id}/locations/{self.location}/publishers/google/models/{model}"
            response = client.predict(
                name=endpoint,
                instances=[{"prompt": prompt}],
                parameters={"temperature": 0.7, "max_output_tokens": 2000},
            )
            return {"status": "success", "output": response.predictions[0]}
        except Exception as e:
            return {"status": "failed", "error": str(e)}
