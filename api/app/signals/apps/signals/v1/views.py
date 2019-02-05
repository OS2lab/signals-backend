"""
Views that are used exclusively by the V1 API
"""
from datapunt_api.pagination import HALPagination
from datapunt_api.rest import DatapuntViewSet
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.views.generic.detail import SingleObjectMixin
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.status import HTTP_202_ACCEPTED
from rest_framework.viewsets import ViewSet

from signals.apps.signals.api_generics.permissions import SIAPermissions
from signals.apps.signals.models import History, MainCategory, Signal, SubCategory
from signals.apps.signals.pdf.views import PDFTemplateView
from signals.apps.signals.v1.serializers import (
    HistoryHalSerializer,
    MainCategoryHALSerializer,
    PrivateSignalSerializerDetail,
    PrivateSignalSerializerList,
    PublicSignalCreateSerializer,
    PublicSignalSerializerDetail,
    SubCategoryHALSerializer,
)
from signals.auth.backend import JWTAuthBackend
from rest_framework_extensions.mixins import DetailSerializerMixin


class MainCategoryViewSet(DatapuntViewSet):
    queryset = MainCategory.objects.all()
    serializer_detail_class = MainCategoryHALSerializer
    serializer_class = MainCategoryHALSerializer
    lookup_field = 'slug'


class SubCategoryViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategoryHALSerializer
    pagination_class = HALPagination

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        obj = get_object_or_404(queryset,
                                main_category__slug=self.kwargs['slug'],
                                slug=self.kwargs['sub_slug'])
        self.check_object_permissions(self.request, obj)
        return obj


class AddAttachmentMixin(ViewSet):

    @action(detail=True, methods=['POST'])
    def attachment(self, request, **kwargs):
        # **kwargs contains the url parameters (pk or uuid or ...)
        signal = Signal.objects.get(**kwargs)

        # Check upload is present and not too big
        file = request.data.get('file', None)
        if file:
            if file.size > 8388608:  # 8MB = 8*1024*1024
                raise ValidationError("Bestand mag maximaal 8Mb groot zijn.")
        else:
            raise ValidationError("File is een verplicht veld.")

        Signal.actions.add_attachment(file, signal)

        return Response({}, status=HTTP_202_ACCEPTED)


class PrivateSignalViewSet(DatapuntViewSet,
                           mixins.CreateModelMixin,
                           mixins.UpdateModelMixin,
                           AddAttachmentMixin):
    """Viewset for `Signal` objects in V1 private API"""
    queryset = Signal.objects.all()
    serializer_class = PrivateSignalSerializerList
    serializer_detail_class = PrivateSignalSerializerDetail
    pagination_class = HALPagination
    authentication_classes = (JWTAuthBackend,)
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (SIAPermissions,)

    http_method_names = ['get', 'post', 'patch', 'head', 'options', 'trace']

    @action(detail=True)
    def history(self, request, pk=None):
        """History endpoint filterable by action."""
        history_entries = History.objects.filter(_signal__id=pk)
        what = self.request.query_params.get('what', None)
        if what:
            history_entries = history_entries.filter(what=what)

        serializer = HistoryHalSerializer(history_entries, many=True)
        return Response(serializer.data)


class PublicSignalViewSet(mixins.CreateModelMixin,
                          DetailSerializerMixin,
                          mixins.RetrieveModelMixin,
                          viewsets.GenericViewSet,
                          AddAttachmentMixin):
    queryset = Signal.objects.all()
    serializer_class = PublicSignalCreateSerializer
    serializer_detail_class = PublicSignalSerializerDetail
    lookup_field = 'signal_id'


class GeneratePdfView(LoginRequiredMixin, SingleObjectMixin, PDFTemplateView):
    object = None
    pk_url_kwarg = 'signal_id'
    queryset = Signal.objects.all()

    template_name = 'signals/pdf/print_signal.html'
    extra_context = {'now': timezone.datetime.now(), }

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        self.pdf_filename = 'SIA-{}.pdf'.format(self.object.pk)
        rd_coordinates = self.object.location.get_rd_coordinates()
        bbox = '{},{},{},{}'.format(
            rd_coordinates.x - 340.00,
            rd_coordinates.y - 125.00,
            rd_coordinates.x + 340.00,
            rd_coordinates.y + 125.00,
        )
        return super(GeneratePdfView, self).get_context_data(bbox=bbox)
