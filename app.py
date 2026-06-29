from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_file
)

from werkzeug.utils import secure_filename

import os
import uuid

import plotly.express as px
import plotly.io as pio

from Linux_processes.Variant_analysis import VariantAnalysis
from Linux_processes.Variant_calling_pipeline import Variant_calling_pipeline


app = Flask(__name__)

# ---------------------------------------------------
# Project Base Directory
# ---------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ---------------------------------------------------
# Landing Page
# ---------------------------------------------------

@app.route('/')
def index():

    return render_template(
        "index.html"
    )


# ---------------------------------------------------
# Run Pipeline
# ---------------------------------------------------

@app.route(
    "/run_pipeline",
    methods=["POST"]
)
def run_pipeline():

    organism = request.form["organism"]

    fastq1 = request.files["fastq1"]
    fastq2 = request.files["fastq2"]

    if not fastq1.filename or not fastq2.filename:

        return "Please upload both R1 and R2 FASTQ files."

    # ----------------------------------------

    run_id = str(
        uuid.uuid4()
    )[:8]

    run_folder = os.path.join(
        BASE_DIR,
        "uploads",
        run_id
    )

    os.makedirs(
        run_folder,
        exist_ok=True
    )

    # ----------------------------------------

    filename1 = secure_filename(
        fastq1.filename
    )

    filename2 = secure_filename(
        fastq2.filename
    )

    uploaded_fastq1 = os.path.join(
        run_folder,
        filename1
    )

    uploaded_fastq2 = os.path.join(
        run_folder,
        filename2
    )

    fastq1.save(
        uploaded_fastq1
    )

    fastq2.save(
        uploaded_fastq2
    )

    # ----------------------------------------
    # Reference Genome
    # ----------------------------------------

    if organism == "ecoli":

        reference_genome = os.path.join(

            BASE_DIR,
            "ref_seq",
            "E_Coli",
            "GCF_000005845.2_ASM584v2_genomic.fna"

        )

    else:

        reference_genome = os.path.join(

            BASE_DIR,
            "ref_seq",
            "sars_cov_2",
            "GCF_009858895.2_ASM985889v3_genomic.fna"

        )

    # ----------------------------------------
    # Debug
    # ----------------------------------------

    print("\n===============================")
    print("Reference :", reference_genome)
    print("FASTQ R1  :", uploaded_fastq1)
    print("FASTQ R2  :", uploaded_fastq2)
    print("Output    :", run_folder)
    print("===============================\n")

    # ----------------------------------------

    pipeline = Variant_calling_pipeline(

        reference_genome,
        uploaded_fastq1,
        uploaded_fastq2,
        run_folder

    )

    pipeline.run_pipeline()

    return redirect(

        url_for(

            "vcf_analysis",

            run_id=run_id

        )

    )


# ---------------------------------------------------
# Variant Analysis Dashboard
# ---------------------------------------------------

@app.route("/variant/<run_id>")
def vcf_analysis(run_id):

    vcf_path = os.path.join(

        BASE_DIR,
        "uploads",
        run_id,
        "variants.vcf"

    )

    vn = VariantAnalysis(vcf_path)

    # ----------------------------------------
    # QUAL Histogram
    # ----------------------------------------

    quals = vn.get_qual_scores()

    fig = px.histogram(

        x=quals,
        nbins=50,
        title="Variant Quality Distribution"

    )

    qual_chart = pio.to_html(

        fig,
        full_html=False

    )

    # ----------------------------------------
    # SNP vs INDEL
    # ----------------------------------------

    snp_count = int(

        vn.get_snp_count()

    )

    indel_count = int(

        vn.get_indel_count()

    )

    fig = px.pie(

        values=[

            snp_count,
            indel_count

        ],

        names=[

            "SNPs",
            "INDELs"

        ],

        hole=0.4

    )

    pie_chart = pio.to_html(

        fig,
        full_html=False

    )

    # ----------------------------------------
    # FILTER Status
    # ----------------------------------------

    filter_data = vn.get_filter_status()

    fig = px.pie(

        values=list(filter_data.values()),
        names=list(filter_data.keys()),
        title="Filter Status"

    )

    filter_chart = pio.to_html(

        fig,
        full_html=False

    )

    # ----------------------------------------
    # Depth Distribution
    # ----------------------------------------

    depths = vn.get_depth_values()

    fig = px.histogram(

        x=depths,
        nbins=50,
        title="Depth Distribution"

    )

    depth_chart = pio.to_html(

        fig,
        full_html=False

    )

    # ----------------------------------------
    # Transition / Transversion
    # ----------------------------------------

    titv = vn.get_titv_ratio()

    fig = px.bar(

        x=[

            "Transitions",
            "Transversions"

        ],

        y=[

            titv["transitions"],
            titv["transversions"]

        ],

        title="Transition vs Transversion"

    )

    titv_chart = pio.to_html(

        fig,
        full_html=False

    )

    # ----------------------------------------
    # Pagination
    # ----------------------------------------

    page = int(

        request.args.get(

            "page",
            1

        )

    )

    variants = vn.get_variant_table(

        page=page,
        per_page=50

    )

    # ----------------------------------------
    # Render Dashboard
    # ----------------------------------------


    

    return render_template(

        "variant_analysis_result.html",

        run_id=run_id,

        total_variants=vn.get_total_variants(),

        snp_count=snp_count,

        indel_count=indel_count,

        avg_qual=vn.get_avg_qual(),

        avg_depth=vn.get_avg_depth(),

        variants=variants,

        qual_chart=qual_chart,

        pie_chart=pie_chart,

        filter_chart=filter_chart,

        depth_chart=depth_chart,

        titv_chart=titv_chart

    )



# ---------------------------------------------------
# Download VCF
# ---------------------------------------------------

@app.route("/download_vcf/<run_id>")
def download_vcf(run_id):

    vcf_path = os.path.join(

        BASE_DIR,
        "uploads",
        run_id,
        "variants.vcf"

    )

    if not os.path.exists(vcf_path):

        return "VCF file not found."

    return send_file(

        vcf_path,
        as_attachment=True,
        download_name="variants.vcf"

    )


# ---------------------------------------------------
# Download BAM
# ---------------------------------------------------

@app.route("/download_bam/<run_id>")
def download_bam(run_id):

    bam_path = os.path.join(

        BASE_DIR,
        "uploads",
        run_id,
        "aligned_marked.bam"

    )

    if not os.path.exists(bam_path):

        return "BAM file not found."

    return send_file(

        bam_path,
        as_attachment=True,
        download_name="aligned_marked.bam"

    )


# ---------------------------------------------------
# Run Flask
# ---------------------------------------------------

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",
        port=5000,
        debug=True

    )