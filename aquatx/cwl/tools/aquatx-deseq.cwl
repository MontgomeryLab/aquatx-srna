#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool

baseCommand: aquatx-deseq

inputs:
  input_file:
    type: File
    inputBinding:
      prefix: --input-file
      itemSeparator: ","
    doc: The merged count table output of aquatx-merge

  outfile_prefix:
    type: string
    inputBinding:
      prefix: --outfile-prefix
    doc: The prefix for naming output files

outputs:
  norm_counts:
    type: File
    outputBinding:
      glob: $(inputs.outfile_prefix)_norm_counts.csv

  comparisons:
    type: File[]
    outputBinding:
      glob: $(inputs.outfile_prefix)_*_*_deseq_table.csv
