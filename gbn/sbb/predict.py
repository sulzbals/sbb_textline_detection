from gbn.lib.util import pil_to_cv2_rgb, cv2_to_pil_gray
from gbn.lib.predict import Predicting
from gbn.tool import OCRD_TOOL

from ocrd import Processor
from ocrd_modelfactory import page_from_file
from ocrd_models.ocrd_page import to_xml
from ocrd_models.ocrd_page_generateds import AlternativeImageType, LabelsType, LabelType, MetadataItemType
from ocrd_utils import concat_padded, getLogger, MIMETYPE_PAGE

import os.path

TOOL = "ocrd-gbn-sbb-predict"

LOG = getLogger("processor.OcrdGbnSbbPredict")
FALLBACK_FILEGRP_IMG = "OCR-D-IMG-PREDICT"

class OcrdGbnSbbPredict(Processor):
    def __init__(self, *args, **kwargs):
        kwargs['ocrd_tool'] = OCRD_TOOL['tools'][TOOL]
        kwargs['version'] = OCRD_TOOL['version']
        super(OcrdGbnSbbPredict, self).__init__(*args, **kwargs)

        if hasattr(self, "output_file_grp"):
            try:
                self.page_grp, self.image_grp = self.output_file_grp.split(',')
                self.output_file_grp = self.page_grp
            except ValueError:
                self.page_grp = self.output_file_grp
                self.image_grp = FALLBACK_FILEGRP_IMG
                LOG.info("No output file group for images specified, falling back to '%s'", FALLBACK_FILEGRP_IMG)

    def _process_element(self, element, element_image, element_xywh, id_suffix, page_id, n, input_file, predictor):
        # Convert PIL to cv2 (RGB):
        element_image, alpha = pil_to_cv2_rgb(element_image)

        # Get labels per-pixel and map them to grayscale:
        predict_image = predictor.predict(element_image) * 255

        # Convert cv2 to PIL (grayscale):
        predict_image = cv2_to_pil_gray(predict_image, alpha)

        # Get file ID of image to be saved:
        file_id = input_file.ID.replace(self.input_file_grp, self.image_grp)

        if file_id == input_file.ID:
            file_id = concat_padded(self.image_grp, n)

        # Concatenate model name to ID:
        file_id += id_suffix + "_" + os.path.splitext(os.path.basename(self.parameter['model']))[0]

        # Save image:
        file_path = self.workspace.save_image_file(
            predict_image,
            file_id,
            page_id=page_id,
            file_grp=self.image_grp
        )

        # Add metadata about saved image:
        element.add_AlternativeImage(
            AlternativeImageType(
                filename=file_path,
                comments=element_xywh['features']
            )
        )

    def process(self):
        # Construct predictor object:
        predictor = Predicting(self.parameter['model'], self.parameter['prediction_algorithm'])

        for (n, input_file) in enumerate(self.input_files):
            LOG.info("Processing input file: %i / %s", n, input_file)

            # Create a new PAGE file from the input file:
            page_id = input_file.pageId or input_file.ID
            pcgts = page_from_file(self.workspace.download_file(input_file))
            page = pcgts.get_Page()

            # Get image from PAGE:
            page_image, page_xywh, _ = self.workspace.image_from_page(page, page_id)

            if self.parameter['operation_level'] == "page":
                self._process_element(
                    page,
                    page_image,
                    page_xywh,
                    "",
                    page_id,
                    n,
                    input_file,
                    predictor
                )
            elif self.parameter['operation_level'] == "region":
                regions = page.get_TextRegion()

                for region_idx, region in enumerate(regions):
                    # Get image from text region:
                    region_image, region_xywh = self.workspace.image_from_segment(region, page_image, page_xywh)

                    self._process_element(
                        region,
                        region_image,
                        region_xywh,
                        "_region%04d" % region_idx,
                        page_id,
                        n,
                        input_file,
                        predictor
                    )
            elif self.parameter['operation_level'] == "line":
                regions = page.get_TextRegion()

                for region_idx, region in enumerate(regions):
                    lines = region.get_TextLine()

                    for line_idx, line in enumerate(lines):
                        # Get image from text region:
                        line_image, line_xywh = self.workspace.image_from_segment(line, page_image, page_xywh)

                        self._process_element(
                            line,
                            line_image,
                            line_xywh,
                            "_region%04d" % region_idx + "_line%04d" % line_idx,
                            page_id,
                            n,
                            input_file,
                            predictor
                        )

            # Add metadata about this operation:
            metadata = pcgts.get_Metadata()
            metadata.add_MetadataItem(
                MetadataItemType(
                    type_="processingStep",
                    name=self.ocrd_tool['steps'][0],
                    value=TOOL,
                    Labels=[
                        LabelsType(
                            externalModel="ocrd-tool",
                            externalId="parameters",
                            Label=[
                                LabelType(
                                    type_=name,
                                    value=self.parameter[name]
                                ) for name in self.parameter.keys()
                            ]
                        )
                    ]
                )
            )

            # Get file ID of XML PAGE to be saved:
            file_id = input_file.ID.replace(self.input_file_grp, self.page_grp)

            if file_id == input_file.ID:
                file_id = concat_padded(self.page_grp, n)

            # Save XML PAGE:
            self.workspace.add_file(
                 ID=file_id,
                 file_grp=self.page_grp,
                 pageId=page_id,
                 mimetype=MIMETYPE_PAGE,
                 local_filename=os.path.join(self.output_file_grp, file_id)+".xml",
                 content=to_xml(pcgts)
            )
