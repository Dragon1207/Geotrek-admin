"""
    Generic views for authentication
"""
import re

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from paperclip.settings import get_attachment_permission, get_attachment_model
from mapentity.views.base import ServeAttachment as BaseServeAttachment


class ServeAttachment(BaseServeAttachment):
    def get(self, request, *args, **kwargs):
        """
            Serve media/ for authorized users only, since it can contain sensitive
            information (uploaded documents)
        """
        path = kwargs['path']
        original_path = re.sub(settings['REGEX_PATH_ATTACHMENTS'], '', path, count=1, flags=re.IGNORECASE)
        attachment = get_object_or_404(get_attachment_model(), attachment_file=original_path)
        obj = attachment.content_object
        import pdb;pdb.set_trace()
        if not obj.is_public() and obj.same_structure(request.user):
            raise PermissionDenied

        response = super().get(request, *args, **kwargs)
        return response
