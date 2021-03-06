#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: Workflow

requirements:
  - class: ScatterFeatureRequirement
  - class: StepInputExpressionRequirement

inputs:
  # multi input
  threads: int?

  # fastp inputs
  in_fq: File[]
  out_fq: string[]
  fp_phred64: boolean?
  compression: int?
  dont_overwrite: boolean?
  disable_adapter_trimming: boolean?
  adapter_sequence: string?
  trim_poly_x: boolean?
  poly_x_min_len: int?
  disable_quality_filtering: boolean?
  qualified_quality_phred: int?
  unqualified_percent_limit: int?
  n_base_limit: int?
  disable_length_filtering: boolean?
  length_required: int?
  length_limit: int?
  overrepresentation_analysis: boolean?
  overrepresentation_sampling: int?
  json: string[]
  html: string[]
  report_title: string[]

  # collapser inputs
  uniq_seq_prefix: string[]
  threshold: int?
  compress: boolean?

  # bowtie inputs
  bt_index_files: File[]
  ebwt: string
  outfile: string[]
  fastq: boolean?
  fasta: boolean?
  trim5: int?
  trim3: int?
  bt_phred64: boolean?
  solexa: boolean?
  solexa13: boolean?
  end_to_end: int?
  nofw: boolean?
  norc: boolean?
  k_aln: int?
  all_aln: boolean?
  no_unal: boolean?
  un: string[]
  sam: boolean?
  seed: int?
  shared_mem: boolean?

  #counter inputs
  ref_annotations: File[]
  mask_annotations: File[]?
  antisense: string[]?
  out_prefix: string[]
  intermed_file: boolean?

  # merge and deseq
  output_file_stats: string
  output_file_counts: string
  output_prefix: string

steps:
  fastp:
    run: ../tools/fastp.cwl
    scatter: [in1, out1, report_title, json, html]
    scatterMethod: dotproduct
    in:
      thread: threads
      in1: in_fq    
      out1: out_fq
      phred64: fp_phred64
      compression: compression
      dont_overwrite: dont_overwrite
      disable_adapter_trimming: disable_adapter_trimming
      adapter_sequence: adapter_sequence 
      trim_poly_x: trim_poly_x
      poly_x_min_len: poly_x_min_len
      disable_quality_filtering: disable_quality_filtering
      qualified_quality_phred: qualified_quality_phred
      unqualified_percent_limit: unqualified_percent_limit
      n_base_limit: n_base_limit
      disable_length_filtering: disable_length_filtering
      length_required: length_required
      length_limit: length_limit
      overrepresentation_analysis: overrepresentation_analysis
      overrepresentation_sampling: overrepresentation_sampling
      json: json
      html: html
      report_title: report_title 
    out: [fastq1, report_json, report_html]

  collapse:
    run: ../tools/aquatx-collapse.cwl
    scatter: [input_file, out_prefix]
    scatterMethod: dotproduct
    in:
      input_file: fastp/fastq1
      out_prefix: uniq_seq_prefix
      threshold: threshold
      compress: compress
    out: [collapsed_fa, low_counts_fa]

  bowtie:
    run: ../tools/bowtie.cwl
    scatter: [reads, outfile, un]
    scatterMethod: dotproduct
    in:
      bt_index_files: bt_index_files
      ebwt: ebwt 
      reads: collapse/collapsed_fa
      outfile: outfile
      fastq: fastq
      fasta: fasta
      trim5: trim5
      trim3: trim3
      phred64: bt_phred64
      solexa: solexa
      solexa13: solexa13
      end_to_end: end_to_end
      nofw: nofw
      k_aln: k_aln
      all_aln: all_aln
      no_unal: no_unal
      un: un
      sam: sam
      threads: threads
      shared_memory: shared_mem
      seed: seed
    out: [sam_out, unal_seqs]

  counts:
    run: ../tools/aquatx-count.cwl
    scatter: [input_file, out_prefix]
    scatterMethod: dotproduct
    in:
      ref_annotations: ref_annotations
      mask_annotations: mask_annotations
      antisense: antisense
      input_file: bowtie/sam_out
      out_prefix: out_prefix
      intermed_file: intermed_file
    out: [feature_counts, other_counts, stats_file, intermed_out_file]

  merge_counts:
    run: ../tools/aquatx-merge.cwl
    in:
      input_files: counts/feature_counts
      sample_names: out_prefix
      mode: 
        valueFrom: "counts"
      output_file: output_file_counts
    out: [merged_file]

  merge_stats:
    run: ../tools/aquatx-merge.cwl
    in:
      input_files: counts/stats_file
      sample_names: out_prefix
      mode: 
        valueFrom: "stats"
      output_file: output_file_stats
    out: [merged_file]

  deseq2:
    run: ../tools/aquatx-deseq.cwl
    in:
      input_file: merge_counts/merged_file
      outfile_prefix: output_prefix
    out: [norm_counts, comparisons]

outputs:
  fastq_clean:  
    type: File[]
    outputSource: fastp/fastq1
  
  html_report_file:
    type: File[]
    outputSource: fastp/report_html

  json_report_file:
    type: File[]
    outputSource: fastp/report_json

  uniq_seqs:
    type: File[]
    outputSource: collapse/collapsed_fa

  aln_seqs:
    type: File[]
    outputSource: bowtie/sam_out
  
  other_count_files:
    type: 
      type: array
      items: 
        type: array
        items: File
    outputSource: counts/other_counts

  feat_count_files:
    type: File[]
    outputSource: counts/feature_counts

  count_stats:
    type: File[]
    outputSource: counts/stats_file

  count_merged:
    type: File
    outputSource: merge_counts/merged_file

  stats_merged: 
    type: File
    outputSource: merge_stats/merged_file

  deseq_normed:
    type: File
    outputSource: deseq2/norm_counts

  deseq_tables:
    type: File[]
    outputSource: deseq2/comparisons

  # Optional outputs
  aln_table:
    type: File[]?
    outputSource: counts/intermed_out_file

  uniq_seqs_low:
    type: File[]?
    outputSource: collapse/low_counts_fa

