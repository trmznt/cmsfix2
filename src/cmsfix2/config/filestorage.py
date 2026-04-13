import fsspec
import pathlib

from advanced_alchemy.types.file_object import FileObject, StoredObject, storages
from advanced_alchemy.types.file_object.backends.fsspec import FSSpecBackend

from litestar_pulse.config import filestorage

STORAGE_DIR = pathlib.Path.cwd() / "storage/cmsfix2"
CMSFIX2_STORAGE = "cmsfix2_storage"


def init_filestorage() -> None:

    filestorage.init_filestorage()

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    local_fs = fsspec.filesystem("file", auto_mkdir=True)

    storages.register_backend(
        FSSpecBackend(
            fs=local_fs,
            key=CMSFIX2_STORAGE,
            # This prepends the path to every file saved via this backend
            prefix=STORAGE_DIR.as_posix(),
        )
    )


# EOF
