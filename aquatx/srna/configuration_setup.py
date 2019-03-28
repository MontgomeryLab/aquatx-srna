"""
This script uses the simple configuration file and spreadsheets to create the
configuration YAML that can be used as input in the CWL workflow.
"""
import os
import datetime
import argparse
from shutil import copyfile
import csv
from pkg_resources import resource_filename
import ruamel.yaml

def get_args():
    """
    Get the input arguments
    """

    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input-file', metavar='CONFIG', required=True,
                        help="Input file")

    args = parser.parse_args()

    return args

def process_sample_sheet(sample_file, config_settings):
    """
    Function to process the input sample sheet.
    """
    sample_files = list()
    sample_identifiers = list()
    sample_out_fq = list()
    sample_report = list()
    sample_uniq_seq = list()
    sample_sams = list()
    sample_unaligned = list()
    sample_low_counts = list()
    sample_json = list()
    sample_html = list()

    with open(sample_file) as sf:
        csv_reader = csv.DictReader(sf, delimiter=',')
        for row in csv_reader:
            sample_basename = os.path.splitext(os.path.basename(row['\ufeffInput FastQ/A Files']))[0]
            sample_files.append({'class': 'File',
                                 'path': row['\ufeffInput FastQ/A Files']})
            sample_identifiers.append(row['Sample/Group Name'] + '_replicate_'
                                      + row['Replicate number'])
            sample_out_fq.append(sample_basename + '_cleaned.fastq')
            sample_report.append(row['Sample/Group Name'] + '_replicate_'
                                 + row['Replicate number'] + '_fastp_report')
            sample_uniq_seq.append(sample_basename + '_unique_seqs_collapsed.fa')
            sample_sams.append(sample_basename + '_aligned_seqs.sam')
            sample_unaligned.append(sample_basename + '_unaligned_seqs.fa')
            sample_low_counts.append(sample_basename + '_low_count_uniq_seqs.fa')
            sample_json.append(sample_basename + '_qc.json')
            sample_html.append(sample_basename + '_qc.html')

    if not config_settings['keep_low_counts']:
        config_settings.pop('keep_low_counts')
    else:
        config_settings['keep_low_counts'] = sample_low_counts

    config_settings['json'] = sample_json
    config_settings['html'] = sample_html
    config_settings['un'] = sample_unaligned
    config_settings['outfile'] = sample_sams
    config_settings['uniq_seq_file'] = sample_uniq_seq
    config_settings['report_title'] = sample_report
    config_settings['out_fq'] = sample_out_fq
    config_settings['in_fq'] = sample_files
    config_settings['out_prefix'] = sample_identifiers


    return config_settings

def process_reference_sheet(ref_file, config_settings):
    """
    Function to process the input reference sheet.
    """
    ref_files = list()
    mask_files = list()
    antisense = list()

    aquatx_extras_path = resource_filename('aquatx', 'extras/')

    with open(ref_file) as rf:
        csv_reader = csv.DictReader(rf, delimiter=',')
        for row in csv_reader:
            if config_settings['run_idx'] and config_settings['ebwt'] == '':
                bt_idx = os.path.splitext(config_settings['ref_genome'])[0]
                config_settings['ebwt'] = bt_idx
            else:
                bt_idx = config_settings['ebwt']
            config_settings['bt_index_files'] = list(({'class': 'File',
                                                        'path': bt_idx + '.1.ebwt'},
                                                       {'class': 'File',
                                                        'path': bt_idx + '.2.ebwt'},
                                                       {'class': 'File',
                                                        'path': bt_idx + '.3.ebwt'},
                                                       {'class': 'File',
                                                        'path': bt_idx + '.4.ebwt'},
                                                       {'class': 'File',
                                                        'path': bt_idx + '.rev.1.ebwt'},
                                                       {'class': 'File',
                                                        'path': bt_idx + '.rev.2.ebwt'}))

            ref_files.append({'class': 'File', 'path': row['Reference Annotation Files']})
            if row['Reference Mask Annotation Files'].lower() in ('none', ''):
                mask_files.append({'class': 'File', 'path': aquatx_extras_path + '_empty_maskfile_aquatx.gff'})
            else:
                mask_files.append({'class': 'File', 'path': row['Reference Mask Annotation Files']})

            if row['Also count antisense?'].lower() in ('true', 'false'):
                antisense.append(row['Also count antisense?'].lower())
            else:
                raise ValueError('The value associated with reference file %s for '
                                 'antisense counting is not true/false.'
                                 % row['Reference Annotation Files'])

    config_settings['ebwt'] = os.path.splitext(os.path.basename(bt_idx))[0]
    config_settings['ref_annotations'] = ref_files
    config_settings['mask_annotations'] = mask_files
    config_settings['antisense'] = antisense

    return config_settings

def setup_config(time, input_file, config_settings):
    """
    Function to set up the configuration file from template
    """
    config_settings['run_date'] = time.split('_')[0]
    config_settings['run_time'] = time.split('_')[1]

    config_settings = process_sample_sheet(config_settings['sample_sheet_file'], config_settings)

    if config_settings['run_directory'] == '':
        config_settings['run_directory'] = time + config_settings['user'] + '_aquatx'
    if config_settings['run_prefix'] == '':
        config_settings['run_prefix'] = time + config_settings['user'] + '_aquatx'
    if config_settings['output_prefix'] == '':
        config_settings['output_prefix'] = config_settings['run_prefix']

    config_settings['output_file_stats'] = config_settings['output_prefix'] + '_run_stats.csv'
    config_settings['output_file_counts'] = config_settings['output_prefix'] + '_raw_counts.csv'

    config_settings = process_reference_sheet(config_settings['reference_sheet_file'],
                                              config_settings)

    if config_settings['adapter_sequence'] == 'auto_detect':
        config_settings.pop('adapter_sequence')

    if os.path.basename(input_file) == 'run_config_template.yml':
        input_name = time + '_run_config.yml'
        copyfile(input_file, input_name)
    else:
        input_name = input_file

    with open(input_name, 'w') as outconf:
        ruamel.yaml.round_trip_dump(config_settings, outconf,
                                    default_flow_style=False, indent=4, block_seq_indent=2)
    
    # output filenames to stdout for running cwltool
    print(input_name, end='')

def setup_workflow(time, config_settings):
    """
    Create the workflow according to configuration
    """
    
    yml = ruamel.yaml.YAML()

    with open("test-wf.cwl", 'w') as cwl:
        ruamel.yaml.round_trip_dump
    pass

def main():
    """
    Main routine to process the run information.
    """

    # Get input config file
    args = get_args()

    # Run time information
    time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    
    # If the template is being used, save as a new file
    yml = ruamel.yaml.YAML()

    with open(args.input_file) as conf:
        config_settings = yml.load(conf)
    
    #TODO: need to specify the non-model organism run when no reference genome is given

    setup_config(time, args.input_file, config_settings)
    setup_workflow(time, config_settings)

if __name__ == '__main__':
    main()