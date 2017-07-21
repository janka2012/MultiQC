from multiqc.modules.base_module import BaseMultiqcModule
import logging
import json
from collections import OrderedDict
from multiqc import config

log = logging.getLogger(__name__)

class MultiqcModule(BaseMultiqcModule):
    def __init__(self):
        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='bcl2fastq', anchor='bcl2fastq',
        href="https://support.illumina.com/downloads/bcl2fastq-conversion-software-v2-18.html",
        info="bcl2fastq can be used to both demultiplex data and convert BCL files to FASTQ file formats for downstream analysis.")

        self.bcl2fastq_bylane = dict()
        self.bcl2fastq_bysample = dict()

        for myfile in self.find_log_files('bcl2fastq'):
            content = json.loads(myfile["f"])
            for conversionResult in content["ConversionResults"]:
                lane = conversionResult["LaneNumber"]
                self.bcl2fastq_bylane[lane] = {"total": 0, "perfectIndex": 0}
                for demuxResult in conversionResult["DemuxResults"]:
                    sample = demuxResult["SampleName"]
                    if not sample in self.bcl2fastq_bysample:
                        self.bcl2fastq_bysample[sample] = {"total": 0, "perfectIndex": 0}
                    self.bcl2fastq_bylane[lane]["total"] += demuxResult["NumberReads"]
                    self.bcl2fastq_bysample[sample]["total"] += demuxResult["NumberReads"]
                    for indexMetric in demuxResult["IndexMetrics"]:
                        self.bcl2fastq_bylane[lane]["perfectIndex"] += indexMetric["MismatchCounts"]["0"]
                        self.bcl2fastq_bysample[sample]["perfectIndex"] += indexMetric["MismatchCounts"]["0"]

        # Filter to strip out ignored sample names
        self.bcl2fastq_bylane = self.ignore_samples(self.bcl2fastq_bylane)
        self.bcl2fastq_bysample = self.ignore_samples(self.bcl2fastq_bysample)

        self.add_general_stats()
        self.write_data_file({str(k): self.bcl2fastq_bylane[k] for k in self.bcl2fastq_bylane.keys()}, 'multiqc_bcl2fastq_bylane')
        self.write_data_file(self.bcl2fastq_bysample, 'multiqc_bcl2fastq_bysample')

        if len(self.bcl2fastq_bylane) == 0 and len(self.bcl2fastq_bysample) == 0:
            log.debug("Could not find any bcl2fastq data in {}".format(config.analysis_dir))
            raise UserWarning

    def add_general_stats(self):
        data = {key: {"total": self.bcl2fastq_bysample[key]["total"], "perfectPercent": '{0:.1f}'.format(100*self.bcl2fastq_bysample[key]["perfectIndex"]/self.bcl2fastq_bysample[key]["total"])} for key in self.bcl2fastq_bysample.keys()}
        headers = OrderedDict()
        headers['total'] = {
            'title': 'Total Reads',
            'description': 'Total number of reads for this sample as determined by bcl2fastq demultiplexing',
            'scale': 'Blues'
        }
        headers['perfectPercent'] = {
            'title': 'Perfect Index Read Percentage',
            'description': 'Percent of reads with perfect index (0 mismatches)',
            'max': 100,
            'min': 0,
            'scale': 'RdYlGn',
            'suffix': '%'
        }
        self.general_stats_addcols(data, headers)
