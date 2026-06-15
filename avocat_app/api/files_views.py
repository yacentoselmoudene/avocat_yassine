"""File transport for PieceJointe binaries.

The sync protocol ships metadata (`pieces/<name>` relative path) but never the
binary. These endpoints close the loop:

  GET  /api/files/<uuid>/  -> binary stream, Content-Disposition: attachment
  POST /api/files/<uuid>/  -> multipart upload (field name `file`)

Idempotent on upload — the same uuid uploaded twice just overwrites. Auth is
JWT-protected like the rest of /api/.
"""
import hashlib
import os
from urllib.parse import quote

from django.http import FileResponse, HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from avocat_app.models import PieceJointe


def _hash(file_obj, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    for chunk in file_obj.chunks(chunk_size):
        h.update(chunk)
    return h.hexdigest()


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def file_endpoint(request, piece_id):
    piece = PieceJointe.all_objects.filter(pk=piece_id).first()
    if piece is None:
        return Response({"detail": "piece not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        if not piece.fichier or not piece.fichier.name:
            return Response({"detail": "no file stored"}, status=status.HTTP_404_NOT_FOUND)
        try:
            f = piece.fichier.open("rb")
        except (FileNotFoundError, OSError):
            return Response({"detail": "file missing on server"}, status=status.HTTP_410_GONE)
        resp = FileResponse(f, as_attachment=True,
                            filename=os.path.basename(piece.fichier.name))
        resp["X-File-Size"] = str(piece.fichier.size)
        return resp

    # POST — accept the upload, overwrite atomically
    upload = request.FILES.get("file")
    if upload is None:
        return Response({"detail": "missing 'file' multipart field"},
                        status=status.HTTP_400_BAD_REQUEST)

    # Delete the previous file (if any) before saving — Django's FileField.save()
    # would otherwise leave the old file orphaned on disk.
    if piece.fichier and piece.fichier.name:
        try:
            piece.fichier.storage.delete(piece.fichier.name)
        except OSError:
            pass

    piece.fichier.save(upload.name, upload, save=False)
    # Bump updated_at so clients pull a fresh metadata row that points at the
    # new path. is_deleted left as-is.
    from django.utils import timezone
    piece.updated_at = timezone.now()
    piece.save(update_fields=["fichier", "updated_at"])

    return Response({
        "ok": True,
        "id": str(piece.pk),
        "path": piece.fichier.name,
        "size": piece.fichier.size,
    })
