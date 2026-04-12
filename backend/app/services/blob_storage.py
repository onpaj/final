from pathlib import Path
from app.config import settings

_LOCAL_FALLBACK = Path(__file__).resolve().parent.parent.parent.parent / "data" / "uploads"


def _use_azure() -> bool:
    return bool(settings.azure_storage_connection_string)


def upload_file(batch_id: str, data: bytes) -> None:
    if _use_azure():
        from azure.storage.blob import BlobServiceClient
        client = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
        blob = client.get_blob_client(container=settings.azure_storage_container, blob=f"{batch_id}.csv")
        blob.upload_blob(data, overwrite=True)
    else:
        _LOCAL_FALLBACK.mkdir(parents=True, exist_ok=True)
        (_LOCAL_FALLBACK / f"{batch_id}.csv").write_bytes(data)


def download_file(batch_id: str) -> bytes | None:
    if _use_azure():
        from azure.storage.blob import BlobServiceClient
        from azure.core.exceptions import ResourceNotFoundError
        client = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
        blob = client.get_blob_client(container=settings.azure_storage_container, blob=f"{batch_id}.csv")
        try:
            return blob.download_blob().readall()
        except ResourceNotFoundError:
            return None
    else:
        path = _LOCAL_FALLBACK / f"{batch_id}.csv"
        return path.read_bytes() if path.exists() else None
