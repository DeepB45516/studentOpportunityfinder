"""
app.py — Flask server for FREE Student Opportunity Finder
Uses: Groq Llama3 (free) + Google/DuckDuckGo search (free)
Run: python app.py → http://localhost:5000
"""

import os
import json
import io
import feedparser
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://student-platform-n3r3.onrender.com",
    "https://*.vercel.app"
]}})

from agents import interview_agent, research_agent, report_agent, verify_skill_agent, proficiency_report_agent


# ══════════════════════════════════════════════════════
# PDF GENERATOR
# ══════════════════════════════════════════════════════
def generate_pdf(report: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_LEFT, TA_CENTER

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    # ── Styles ──────────────────────────────────────────
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle("title",
        fontName="Helvetica-Bold", fontSize=22,
        textColor=colors.HexColor("#0a0a0f"),
        spaceAfter=4, leading=26)

    style_subtitle = ParagraphStyle("subtitle",
        fontName="Helvetica", fontSize=10,
        textColor=colors.HexColor("#78716c"),
        spaceAfter=2)

    style_summary = ParagraphStyle("summary",
        fontName="Helvetica", fontSize=10,
        textColor=colors.HexColor("#1c1917"),
        backColor=colors.HexColor("#f5f3ee"),
        borderPad=8, leading=16,
        spaceAfter=6)

    style_section = ParagraphStyle("section",
        fontName="Helvetica-Bold", fontSize=13,
        textColor=colors.HexColor("#0a0a0f"),
        spaceBefore=14, spaceAfter=6)

    style_opp_title = ParagraphStyle("opp_title",
        fontName="Helvetica-Bold", fontSize=10,
        textColor=colors.HexColor("#0a0a0f"),
        spaceAfter=2)

    style_opp_detail = ParagraphStyle("opp_detail",
        fontName="Helvetica", fontSize=9,
        textColor=colors.HexColor("#44403c"),
        leading=14, spaceAfter=2)

    style_why = ParagraphStyle("why",
        fontName="Helvetica-Oblique", fontSize=9,
        textColor=colors.HexColor("#92400e"),
        backColor=colors.HexColor("#fffbeb"),
        borderPad=5, leading=13, spaceAfter=4)

    style_link = ParagraphStyle("link",
        fontName="Helvetica", fontSize=9,
        textColor=colors.HexColor("#1a56db"),
        spaceAfter=6)

    style_pick = ParagraphStyle("pick",
        fontName="Helvetica-Bold", fontSize=10,
        textColor=colors.HexColor("#ff5c00"),
        spaceAfter=2)

    style_action = ParagraphStyle("action",
        fontName="Helvetica", fontSize=9,
        textColor=colors.HexColor("#1c1917"),
        leading=15, spaceAfter=3)

    # ── Build content ────────────────────────────────────
    story = []
    now = datetime.now().strftime("%d %B %Y, %I:%M %p")

    # Header
    story.append(Paragraph("🎓 Student Opportunity Report", style_title))
    story.append(Paragraph(f"Generated on {now}  ·  Powered by Agentic AI", style_subtitle))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0a0a0f"), spaceAfter=10))

    # Student summary
    summary = report.get("student_summary", "")
    if summary:
        story.append(Paragraph(f"<b>Profile:</b> {summary}", style_summary))
        story.append(Spacer(1, 6))

    # Stats row
    total = report.get("total_opportunities", 0)
    cats  = len(report.get("categories", []))
    picks = len(report.get("top_picks", []))
    stats_data = [
        [f"{total}\nOpportunities Found", f"{cats}\nCategories", f"{picks}\nTop Picks"]
    ]
    stats_table = Table(stats_data, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    stats_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), colors.HexColor("#ff5c00")),
        ("TEXTCOLOR",    (0,0), (-1,-1), colors.white),
        ("FONTNAME",     (0,0), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 11),
        ("ALIGN",        (0,0), (-1,-1), "CENTER"),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("ROWHEIGHT",    (0,0), (-1,-1), 36),
        ("GRID",         (0,0), (-1,-1), 1, colors.white),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 14))

    # ── Top Picks ────────────────────────────────────────
    top_picks = report.get("top_picks", [])
    if top_picks:
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d6d0c4"), spaceAfter=6))
        story.append(Paragraph("⭐  Top Picks For You", style_section))
        for p in top_picks:
            story.append(Paragraph(f"#{p.get('rank','')}  {p.get('title','')}", style_pick))
            story.append(Paragraph(p.get("reason",""), style_opp_detail))
            link = p.get("apply_link","#")
            story.append(Paragraph(f'Apply → <a href="{link}" color="#1a56db">{link}</a>', style_link))
            story.append(Spacer(1, 4))

    # ── Categories ───────────────────────────────────────
    for cat in report.get("categories", []):
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d6d0c4"), spaceAfter=6))
        emoji = cat.get("emoji","📌")
        name  = cat.get("name","")
        count = cat.get("count", len(cat.get("opportunities",[])))
        story.append(Paragraph(f"{emoji}  {name}  ({count} found)", style_section))

        for opp in cat.get("opportunities", []):
            story.append(Paragraph(opp.get("title","Opportunity"), style_opp_title))

            # Meta table
            meta = [
                ["Organizer",  opp.get("organizer","—"),
                 "Deadline",   opp.get("deadline","Check website")],
                ["Prize/Stipend", opp.get("stipend_prize","N/A"),
                 "Difficulty", opp.get("difficulty","—")],
                ["Eligibility", opp.get("eligibility","—"), "", ""],
            ]
            meta_table = Table(meta, colWidths=[2.8*cm, 5*cm, 2.8*cm, 5*cm])
            meta_table.setStyle(TableStyle([
                ("FONTNAME",  (0,0), (-1,-1), "Helvetica"),
                ("FONTSIZE",  (0,0), (-1,-1), 8),
                ("TEXTCOLOR", (0,0), (0,-1), colors.HexColor("#78716c")),
                ("TEXTCOLOR", (2,0), (2,-1), colors.HexColor("#78716c")),
                ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
                ("FONTNAME",  (2,0), (2,-1), "Helvetica-Bold"),
                ("VALIGN",    (0,0), (-1,-1), "TOP"),
                ("TOPPADDING",(0,0), (-1,-1), 2),
                ("BOTTOMPADDING",(0,0),(-1,-1), 2),
            ]))
            story.append(meta_table)

            why = opp.get("why_suitable","")
            if why:
                story.append(Paragraph(f"💡 {why}", style_why))

            link = opp.get("apply_link","#")
            story.append(Paragraph(
                f'🔗 Apply: <a href="{link}" color="#1a56db">{link}</a>',
                style_link
            ))
            story.append(Spacer(1, 6))

    # ── Action Plan ──────────────────────────────────────
    action_plan = report.get("action_plan", [])
    if action_plan:
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0a0a0f"), spaceAfter=8))
        story.append(Paragraph("🗺  Your Personal Action Plan", style_section))
        for step in action_plan:
            story.append(Paragraph(f"  ▸  {step}", style_action))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d6d0c4"), spaceAfter=4))
    story.append(Paragraph(
        "Generated by Student Opportunity Finder · Agentic AI System · 3-Agent Pipeline",
        style_subtitle
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ══════════════════════════════════════════════════════
# PROFICIENCY REPORT PDF GENERATOR
# ══════════════════════════════════════════════════════
def generate_prof_pdf(report: dict, score: int, profile: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.graphics.shapes import Drawing, Circle, String
    from reportlab.lib.enums import TA_CENTER

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    s_title   = ParagraphStyle("pt", fontName="Helvetica-Bold", fontSize=20,
                    textColor=colors.HexColor("#0a0a0f"), spaceAfter=4, leading=24)
    s_sub     = ParagraphStyle("ps", fontName="Helvetica", fontSize=9,
                    textColor=colors.HexColor("#78716c"), spaceAfter=2)
    s_section = ParagraphStyle("pse", fontName="Helvetica-Bold", fontSize=12,
                    textColor=colors.HexColor("#0a0a0f"), spaceBefore=14, spaceAfter=6)
    s_body    = ParagraphStyle("pb", fontName="Helvetica", fontSize=9,
                    textColor=colors.HexColor("#1c1917"), leading=15, spaceAfter=4)
    s_orange  = ParagraphStyle("po", fontName="Helvetica-Bold", fontSize=9,
                    textColor=colors.HexColor("#ff5c00"), spaceAfter=3)
    s_green   = ParagraphStyle("pg", fontName="Helvetica", fontSize=9,
                    textColor=colors.HexColor("#059669"), leading=14, spaceAfter=3)
    s_red     = ParagraphStyle("pr", fontName="Helvetica", fontSize=9,
                    textColor=colors.HexColor("#dc2626"), leading=14, spaceAfter=3)
    s_rec     = ParagraphStyle("prec", fontName="Helvetica", fontSize=9,
                    textColor=colors.HexColor("#e5e7eb"), leading=14, spaceAfter=3)

    story = []
    now = datetime.now().strftime("%d %B %Y, %I:%M %p")
    field   = profile.get("What is your field of study?", report.get("domain_title", "Domain"))
    skills  = profile.get("List your top 3 technical skills", "")

    # Header
    story.append(Paragraph("📊 Domain Proficiency Report", s_title))
    story.append(Paragraph(f"Generated on {now}  ·  Powered by CareerAI Skill Verification", s_sub))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0a0a0f"), spaceAfter=10))

    # Score + level banner
    level   = report.get("level", "Intermediate")
    lv_col  = {"Expert":"#059669","Proficient":"#d97706","Intermediate":"#ff5c00","Beginner":"#dc2626"}.get(level,"#ff5c00")
    banner  = [[f"Score: {score}%", level, report.get("domain_title", field)]]
    bt = Table(banner, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    bt.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(0,0), colors.HexColor("#0a0a0f")),
        ("BACKGROUND",  (1,0),(1,0), colors.HexColor(lv_col)),
        ("BACKGROUND",  (2,0),(2,0), colors.HexColor("#f5f3ee")),
        ("TEXTCOLOR",   (0,0),(1,0), colors.white),
        ("TEXTCOLOR",   (2,0),(2,0), colors.HexColor("#0a0a0f")),
        ("FONTNAME",    (0,0),(-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0),(-1,-1), 11),
        ("ALIGN",       (0,0),(-1,-1), "CENTER"),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("ROWHEIGHT",   (0,0),(-1,-1), 34),
        ("GRID",        (0,0),(-1,-1), 1, colors.white),
    ]))
    story.append(bt)
    story.append(Spacer(1, 10))

    # Efficiency summary
    summary = report.get("efficiency_summary", "")
    if summary:
        story.append(Paragraph(f"<b>Summary:</b> {summary}", s_body))
        story.append(Paragraph(f"<b>Career Readiness:</b> {report.get('career_readiness','')}", s_body))
        story.append(Spacer(1, 6))

    # Skill scores table
    skill_scores = report.get("skill_scores", [])
    if skill_scores:
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d6d0c4"), spaceAfter=6))
        story.append(Paragraph("Skill Breakdown", s_section))
        ss_data = [["Skill Area", "Score", "Rating"]] + [
            [s["skill"], f"{s['score']}%",
             "Strong" if s["score"] >= 70 else "Moderate" if s["score"] >= 40 else "Needs Work"]
            for s in skill_scores
        ]
        ss_table = Table(ss_data, colWidths=[8*cm, 3*cm, 5.5*cm])
        ss_table.setStyle(TableStyle([
            ("BACKGROUND",   (0,0),(-1,0),  colors.HexColor("#0a0a0f")),
            ("TEXTCOLOR",    (0,0),(-1,0),  colors.white),
            ("FONTNAME",     (0,0),(-1,0),  "Helvetica-Bold"),
            ("FONTNAME",     (0,1),(-1,-1), "Helvetica"),
            ("FONTSIZE",     (0,0),(-1,-1), 9),
            ("ROWHEIGHT",    (0,0),(-1,-1), 22),
            ("ALIGN",        (1,0),(-1,-1), "CENTER"),
            ("GRID",         (0,0),(-1,-1), 0.5, colors.HexColor("#d6d0c4")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#f5f3ee")]),
        ]))
        story.append(ss_table)
        story.append(Spacer(1, 8))

    # Strengths & Gaps side by side
    strengths = report.get("strengths", [])
    gaps      = report.get("gaps", [])
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d6d0c4"), spaceAfter=6))
    str_items = "\n".join([f"  ✔  {s}" for s in strengths])
    gap_items = "\n".join([f"  ✘  {g}" for g in gaps])
    sg_data = [["✅  Strengths", "⚠️  Gaps to Address"],
               [str_items or "—", gap_items or "—"]]
    sg_table = Table(sg_data, colWidths=[8.25*cm, 8.25*cm])
    sg_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(0,0), colors.HexColor("#f0fdf4")),
        ("BACKGROUND",   (1,0),(1,0), colors.HexColor("#fff5f5")),
        ("FONTNAME",     (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0),(-1,-1), 9),
        ("TEXTCOLOR",    (0,0),(0,0), colors.HexColor("#059669")),
        ("TEXTCOLOR",    (1,0),(1,0), colors.HexColor("#dc2626")),
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("GRID",         (0,0),(-1,-1), 0.5, colors.HexColor("#d6d0c4")),
        ("TOPPADDING",   (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("LEFTPADDING",  (0,0),(-1,-1), 10),
    ]))
    story.append(sg_table)
    story.append(Spacer(1, 10))

    # Recommendations
    recs = report.get("recommendations", [])
    if recs:
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d6d0c4"), spaceAfter=6))
        story.append(Paragraph("🎯  Recommendations", s_section))
        for i, rec in enumerate(recs, 1):
            story.append(Paragraph(f"  {i}.  {rec}", s_body))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d6d0c4"), spaceAfter=4))
    story.append(Paragraph("Generated by CareerAI · Skill Verification System", s_sub))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ══════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/interview", methods=["POST"])
def api_interview():
    body = request.get_json(force=True)
    user_input = (body.get("input") or "").strip()
    if not user_input:
        return jsonify({"success": False, "error": "Please describe what you are looking for."}), 400
    try:
        result = interview_agent(user_input)
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/verify-skill", methods=["POST"])
def api_verify_skill():
    body   = request.get_json(force=True)
    skills = (body.get("skills") or "general programming").strip()
    field  = (body.get("field")  or "engineering").strip()
    try:
        result = verify_skill_agent(skills, field)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/proficiency-report", methods=["POST"])
def api_proficiency_report():
    body     = request.get_json(force=True)
    skills   = (body.get("skills")   or "general programming").strip()
    field    = (body.get("field")    or "engineering").strip()
    score    = int(body.get("score", 0))
    answered = body.get("answered", [])
    try:
        result = proficiency_report_agent(skills, field, score, answered)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/download-prof-pdf", methods=["POST"])
def api_download_prof_pdf():
    """Generate and return a PDF proficiency report."""
    body    = request.get_json(force=True)
    report  = body.get("report", {})
    score   = int(body.get("score", 0))
    profile = body.get("profile", {})
    if not report:
        return jsonify({"error": "No report data provided"}), 400
    try:
        pdf_bytes = generate_prof_pdf(report, score, profile)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"proficiency_report_{ts}.pdf"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/research", methods=["POST"])
def api_research():
    body       = request.get_json(force=True)
    profile    = body.get("profile", {})
    categories = body.get("categories", ["Hackathon", "Internship", "Scholarship", "Competition"])

    if not profile:
        return jsonify({"success": False, "error": "Profile is required."}), 400

    try:
        research = research_agent(profile, categories)
        report   = report_agent(profile, research["results"])

        os.makedirs("output", exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"output/report_{ts}.json"
        with open(path, "w") as f:
            json.dump(report, f, indent=2)

        return jsonify({
            "success": True,
            "report":  report,
            "logs":    research["logs"],
            "file":    path,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/download/<path:filename>")
def api_download(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404
    return send_file(path, as_attachment=True)


@app.route("/api/download-pdf", methods=["POST"])
def api_download_pdf():
    """Generate and return a PDF from the report JSON."""
    body   = request.get_json(force=True)
    report = body.get("report")
    if not report:
        return jsonify({"error": "No report data provided"}), 400
    try:
        pdf_bytes = generate_pdf(report)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"opportunity_report_{ts}.pdf"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════
# RESUME PDF GENERATOR
# ══════════════════════════════════════════════════════
def generate_resume_pdf(resume: dict, template: str = "classic") -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable)
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm)

    W = A4[0] - 4*cm  # usable width

    # ── colour palette per template ────────────────────
    if template == "modern":
        hdr_bg   = colors.HexColor("#0a0a0f")
        acc      = colors.HexColor("#059669")
        acc2     = colors.HexColor("#34d399")
        hdr_fg   = colors.white
        sec_fg   = colors.HexColor("#0a0a0f")
    elif template == "minimal":
        hdr_bg   = colors.HexColor("#f9f7f4")
        acc      = colors.HexColor("#1a1a1a")
        acc2     = colors.HexColor("#888888")
        hdr_fg   = colors.HexColor("#1a1a1a")
        sec_fg   = colors.HexColor("#999999")
    else:  # classic
        hdr_bg   = None
        acc      = colors.HexColor("#0a0a0f")
        acc2     = colors.HexColor("#1a56db")
        hdr_fg   = colors.HexColor("#0a0a0f")
        sec_fg   = colors.HexColor("#888888")

    p = resume.get("personal", {})
    education    = resume.get("education", [])
    experience   = resume.get("experience", [])
    skills       = resume.get("skills", {})
    projects     = resume.get("projects", [])
    certs        = resume.get("certs", [])
    awards       = resume.get("awards", [])
    languages    = resume.get("languages", [])
    volunteer    = resume.get("volunteer", [])

    # ── Styles ─────────────────────────────────────────
    s_name = ParagraphStyle("rn", fontName="Helvetica-Bold",
        fontSize=22, leading=26, textColor=hdr_fg if template != "classic" else acc,
        spaceAfter=3)
    s_title_p = ParagraphStyle("rt", fontName="Helvetica",
        fontSize=10, textColor=colors.HexColor("#666666"), spaceAfter=4)
    s_contact = ParagraphStyle("rc", fontName="Helvetica",
        fontSize=8, textColor=colors.HexColor("#555555"), spaceAfter=2, leading=12)
    s_sec = ParagraphStyle("rs", fontName="Helvetica-Bold",
        fontSize=8, textColor=sec_fg, spaceBefore=10, spaceAfter=5,
        leading=11, letterSpacing=1.5)
    s_body = ParagraphStyle("rb", fontName="Helvetica",
        fontSize=9, textColor=colors.HexColor("#333333"), leading=14, spaceAfter=2)
    s_bold = ParagraphStyle("rbd", fontName="Helvetica-Bold",
        fontSize=9.5, textColor=colors.HexColor("#0a0a0f"), leading=13, spaceAfter=1)
    s_muted = ParagraphStyle("rm", fontName="Helvetica",
        fontSize=8, textColor=colors.HexColor("#777777"), leading=11, spaceAfter=2)
    s_blue = ParagraphStyle("rbl", fontName="Helvetica",
        fontSize=8.5, textColor=acc2, leading=12, spaceAfter=2)
    s_bullet = ParagraphStyle("rbul", fontName="Helvetica",
        fontSize=8.5, textColor=colors.HexColor("#333333"), leading=13,
        leftIndent=12, spaceAfter=1)

    story = []

    def hr(color=colors.HexColor("#d6d0c4"), thick=1):
        return HRFlowable(width="100%", thickness=thick, color=color, spaceAfter=6)

    def sec_title(txt):
        story.append(hr())
        story.append(Paragraph(txt.upper(), s_sec))

    # ── HEADER ─────────────────────────────────────────
    name = p.get("name") or "Your Name"
    if template == "modern":
        # Dark header block using a table
        contact_parts = [x for x in [
            p.get("email"), p.get("phone"), p.get("location"),
            p.get("linkedin"), p.get("github")
        ] if x]
        hdr_data = [[
            Paragraph(name, ParagraphStyle("hn", fontName="Helvetica-Bold",
                fontSize=22, textColor=colors.white, leading=26)),
        ]]
        hdr_t = Table(hdr_data, colWidths=[W])
        hdr_t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), hdr_bg),
            ("TOPPADDING",  (0,0), (-1,-1), 16),
            ("BOTTOMPADDING",(0,0),(-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING",(0,0), (-1,-1), 0),
        ]))
        story.append(hdr_t)
        if p.get("title"):
            story.append(Paragraph(p["title"],
                ParagraphStyle("ht", fontName="Helvetica", fontSize=9.5,
                    textColor=colors.HexColor("#aaaaaa"), spaceAfter=4)))
        story.append(Paragraph(" · ".join(contact_parts), s_contact))
        story.append(Spacer(1, 8))
    else:
        story.append(Paragraph(name, s_name))
        if p.get("title"):
            story.append(Paragraph(p["title"], s_title_p))
        contact_parts = [x for x in [
            p.get("email"), p.get("phone"), p.get("location"),
            p.get("linkedin"), p.get("github"), p.get("website")
        ] if x]
        if contact_parts:
            story.append(Paragraph(" · ".join(contact_parts), s_contact))
        story.append(hr(acc, 2))

    # ── SUMMARY ────────────────────────────────────────
    if p.get("summary"):
        sec_title("Summary")
        story.append(Paragraph(p["summary"], s_body))

    # ── EXPERIENCE ─────────────────────────────────────
    if experience:
        sec_title("Experience")
        for exp in experience:
            title_txt = exp.get("title","")
            company   = exp.get("company","")
            duration  = exp.get("duration","")
            if title_txt or company:
                row = [[Paragraph(title_txt, s_bold),
                        Paragraph(duration, ParagraphStyle("rd",fontName="Helvetica",
                            fontSize=8, textColor=colors.HexColor("#777777"),
                            leading=11, alignment=TA_RIGHT))]]
                t = Table(row, colWidths=[W*0.7, W*0.3])
                t.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),0),
                    ("BOTTOMPADDING",(0,0),(-1,-1),1)]))
                story.append(t)
            if company:
                story.append(Paragraph(company, s_blue))
            for b in exp.get("bullets", []):
                if b:
                    story.append(Paragraph("• " + b, s_bullet))
            story.append(Spacer(1, 5))

    # ── EDUCATION ──────────────────────────────────────
    if education:
        sec_title("Education")
        for edu in education:
            degree = edu.get("degree","")
            inst   = edu.get("institution","")
            year   = edu.get("year","")
            gpa    = edu.get("gpa","")
            if degree:
                row = [[Paragraph(degree, s_bold),
                        Paragraph(year, ParagraphStyle("ry",fontName="Helvetica",
                            fontSize=8, textColor=colors.HexColor("#777777"),
                            leading=11, alignment=TA_RIGHT))]]
                t = Table(row, colWidths=[W*0.7, W*0.3])
                t.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),0),
                    ("BOTTOMPADDING",(0,0),(-1,-1),1)]))
                story.append(t)
            if inst:
                story.append(Paragraph(inst, s_blue))
            extras = []
            if gpa:   extras.append("GPA: " + gpa)
            if edu.get("courses"): extras.append("Courses: " + edu["courses"])
            if extras:
                story.append(Paragraph(" · ".join(extras), s_muted))
            story.append(Spacer(1, 4))

    # ── SKILLS + PROJECTS side by side ─────────────────
    tech = skills.get("tech", [])
    soft = skills.get("soft", [])
    all_skills = tech + soft
    skill_str = ", ".join(all_skills) if all_skills else ""

    if skill_str or projects:
        sec_title("Skills & Projects")
        left_items = []
        if skill_str:
            left_items.append(Paragraph("Technical: " + ", ".join(tech), s_body))
        if soft:
            left_items.append(Paragraph("Soft Skills: " + ", ".join(soft), s_muted))
        right_items = []
        for proj in projects:
            if proj.get("title"):
                right_items.append(Paragraph(proj["title"], s_bold))
            if proj.get("tech"):
                right_items.append(Paragraph(proj["tech"], s_muted))
            if proj.get("description"):
                right_items.append(Paragraph(proj["description"],
                    ParagraphStyle("pd",fontName="Helvetica",fontSize=8,
                        textColor=colors.HexColor("#444444"),leading=12,spaceAfter=6)))
        if left_items or right_items:
            max_len = max(len(left_items), len(right_items))
            while len(left_items) < max_len: left_items.append(Spacer(1,1))
            while len(right_items) < max_len: right_items.append(Spacer(1,1))
            tdata = [[left_items, right_items]]
            t = Table(tdata, colWidths=[W*0.48, W*0.48])
            t.setStyle(TableStyle([
                ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("TOPPADDING",(0,0),(-1,-1),0),
                ("BOTTOMPADDING",(0,0),(-1,-1),0),
                ("LEFTPADDING",(0,0),(-1,-1),0),
                ("RIGHTPADDING",(0,0),(-1,-1),8),
            ]))
            story.append(t)

    # ── CERTIFICATIONS ─────────────────────────────────
    if certs:
        sec_title("Certifications")
        for cert in certs:
            name_txt = cert.get("name","")
            issuer   = cert.get("issuer","")
            year     = cert.get("year","")
            if name_txt:
                row = [[Paragraph(name_txt + ((" — " + issuer) if issuer else ""), s_body),
                        Paragraph(year, s_muted)]]
                t = Table(row, colWidths=[W*0.8, W*0.2])
                t.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),0),
                    ("BOTTOMPADDING",(0,0),(-1,-1),2),
                    ("ALIGN",(1,0),(1,-1),"RIGHT")]))
                story.append(t)

    # ── AWARDS & HONORS ────────────────────────────────
    awards_list = [a for a in awards if a.get("title")]
    if awards_list:
        sec_title("Awards & Honors")
        for award in awards_list:
            title_txt = award.get("title","")
            issuer    = award.get("issuer","")
            year      = award.get("year","")
            desc      = award.get("description","")
            label     = title_txt + ((" — " + issuer) if issuer else "")
            row = [[Paragraph(label, s_bold), Paragraph(year, s_muted)]]
            t = Table(row, colWidths=[W*0.8, W*0.2])
            t.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),0),
                ("BOTTOMPADDING",(0,0),(-1,-1),1),
                ("ALIGN",(1,0),(1,-1),"RIGHT")]))
            story.append(t)
            if desc:
                story.append(Paragraph(desc, s_body))
            story.append(Spacer(1, 4))

    # ── LANGUAGES ──────────────────────────────────────
    lang_list = [l for l in languages if l.get("language")]
    if lang_list:
        sec_title("Languages")
        lang_str = "  ·  ".join(
            l["language"] + (" (" + l.get("proficiency","") + ")" if l.get("proficiency") else "")
            for l in lang_list
        )
        story.append(Paragraph(lang_str, s_body))

    # ── VOLUNTEER EXPERIENCE ───────────────────────────
    vol_list = [v for v in volunteer if v.get("role")]
    if vol_list:
        sec_title("Volunteer Experience")
        for vol in vol_list:
            role     = vol.get("role","")
            org      = vol.get("organization","")
            duration = vol.get("duration","")
            desc     = vol.get("description","")
            if role:
                row = [[Paragraph(role, s_bold),
                        Paragraph(duration, ParagraphStyle("vd", fontName="Helvetica",
                            fontSize=8, textColor=colors.HexColor("#777777"),
                            leading=11, alignment=TA_RIGHT))]]
                t = Table(row, colWidths=[W*0.7, W*0.3])
                t.setStyle(TableStyle([("TOPPADDING",(0,0),(-1,-1),0),
                    ("BOTTOMPADDING",(0,0),(-1,-1),1)]))
                story.append(t)
            if org:
                story.append(Paragraph(org, s_blue))
            if desc:
                story.append(Paragraph(desc, s_body))
            story.append(Spacer(1, 5))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


@app.route("/api/resume-pdf", methods=["POST"])
def api_resume_pdf():
    """Generate and return a clean PDF resume from JSON data."""
    body     = request.get_json(force=True)
    resume   = body.get("resume", {})
    template = body.get("template", "classic")
    if not resume:
        return jsonify({"error": "No resume data provided"}), 400
    # Sanitise — ensure skills/lists are always correct types
    if not isinstance(resume.get("skills"), dict):
        resume["skills"] = {"tech": [], "soft": []}
    resume["skills"].setdefault("tech", [])
    resume["skills"].setdefault("soft", [])
    for key in ["education", "experience", "projects", "certs", "awards", "languages", "volunteer"]:
        if not isinstance(resume.get(key), list):
            resume[key] = []
    # Sanitise personal fields
    if not isinstance(resume.get("personal"), dict):
        resume["personal"] = {}
    try:
        pdf_bytes = generate_resume_pdf(resume, template)
        name = (resume.get("personal", {}).get("name") or "resume").replace(" ", "_")
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"resume_{name}_{ts}.pdf"
        )
    except Exception as e:
        import traceback
        print("[Resume PDF Error]", traceback.format_exc())
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════
# AI DAILY — News Engine Routes
# ══════════════════════════════════════════════════════
import feedparser
import hashlib

AI_DAILY_DIR = os.path.join(os.path.dirname(__file__), "output", "ai_daily")
os.makedirs(AI_DAILY_DIR, exist_ok=True)

RSS_FEEDS = [
    {"name": "TechCrunch AI",    "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "MIT Tech Review",  "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/"},
    {"name": "The Verge AI",     "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"},
    {"name": "VentureBeat AI",   "url": "https://venturebeat.com/category/ai/feed/"},
]


@app.route("/api/raw-news")
def api_raw_news():
    """Fetch latest articles from RSS feeds."""
    import re as _re
    import urllib.request

    # Use a browser-like User-Agent so feeds don't block us
    UA = "Mozilla/5.0 (compatible; StudentPlatform/1.0; +https://github.com)"

    articles = []
    for feed in RSS_FEEDS:
        try:
            # Fetch raw XML with proper headers, then parse
            req = urllib.request.Request(feed["url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw_xml = resp.read()
            parsed = feedparser.parse(raw_xml)
            for item in parsed.entries[:5]:
                content = (
                    item.get("summary", "") or
                    (item.get("content") or [{}])[0].get("value", "") or ""
                )
                content = _re.sub(r"<[^>]+>", " ", content).strip()
                content = " ".join(content.split())[:400]
                articles.append({
                    "title":   item.get("title", ""),
                    "content": content,
                    "link":    item.get("link", "#"),
                    "pubDate": item.get("published", ""),
                    "source":  feed["name"],
                })
        except Exception as e:
            print(f"RSS error [{feed['name']}]: {e}")
    return jsonify(articles)


@app.route("/api/ai-daily/newsletters")
def api_list_newsletters():
    """List all generated newsletters, newest first."""
    files = sorted(
        [f for f in os.listdir(AI_DAILY_DIR) if f.endswith(".json") and f.startswith("nl_")],
        reverse=True
    )
    newsletters = []
    for f in files[:20]:
        try:
            with open(os.path.join(AI_DAILY_DIR, f)) as fh:
                nl = json.load(fh)
                newsletters.append({
                    "id":      nl.get("id"),
                    "date":    nl.get("date"),
                    "insight": nl.get("insight", ""),
                    "count":   len(nl.get("articles", [])),
                })
        except Exception:
            pass
    return jsonify(newsletters)


@app.route("/api/ai-daily/newsletter/<nl_id>")
def api_get_newsletter(nl_id):
    """Get a specific newsletter by ID."""
    # Sanitize ID
    nl_id = nl_id.replace("..", "").replace("/", "")
    path = os.path.join(AI_DAILY_DIR, f"nl_{nl_id}.json")
    if not os.path.exists(path):
        return jsonify({"error": "Not found"}), 404
    with open(path) as f:
        return jsonify(json.load(f))


@app.route("/api/ai-daily/generate", methods=["POST"])
def api_generate_newsletter():
    """Generate today's AI Daily newsletter using Gemini."""
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        return jsonify({"success": False, "error": "GEMINI_API_KEY not set in .env"}), 500

    import re as _re
    import urllib.request as _ur
    import requests as _req
    from groq import Groq as _Groq

    GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"

    def gemini(prompt: str) -> str:
        """Try Gemini first; fall back to Groq (llama-3.1-8b-instant) on any error."""
        # ── Attempt 1: Gemini ──────────────────────────────
        if gemini_key:
            try:
                resp = _req.post(
                    GEMINI_URL,
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=20,
                )
                resp.raise_for_status()
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                print(f"❌ GEMINI ERROR (falling back to Groq): {e}")

        # ── Attempt 2: Groq fallback ───────────────────────
        groq_key = os.getenv("GROQ_API_KEY", "")
        if not groq_key:
            raise Exception("Both Gemini and Groq unavailable (no GROQ_API_KEY set)")
        try:
            _groq_client = _Groq(api_key=groq_key)
            response = _groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            result = response.choices[0].message.content.strip()
            print("✅ Groq fallback succeeded")
            return result
        except Exception as ge:
            raise Exception(f"Both Gemini and Groq failed. Groq error: {ge}")
    # 1. Fetch raw news
    UA = "Mozilla/5.0 (compatible; StudentPlatform/1.0)"
    try:
        raw_articles = []
        for feed in RSS_FEEDS:
            try:
                req = _ur.Request(feed["url"], headers={"User-Agent": UA})
                with _ur.urlopen(req, timeout=10) as resp:
                    raw_xml = resp.read()
                parsed = feedparser.parse(raw_xml)
                for item in parsed.entries[:4]:
                    content = (item.get("summary", "") or "")
                    content = _re.sub(r"<[^>]+>", " ", content).strip()
                    content = " ".join(content.split())[:300]
                    raw_articles.append({
                        "title":   item.get("title", ""),
                        "content": content,
                        "link":    item.get("link", "#"),
                        "pubDate": item.get("published", ""),
                        "source":  feed["name"],
                    })
            except Exception as fe:
                print(f"Feed error [{feed['name']}]: {fe}")
    except Exception as e:
        return jsonify({"success": False, "error": f"RSS fetch failed: {e}"}), 500

    if not raw_articles:
        return jsonify({"success": False, "error": "No articles fetched from RSS feeds"}), 500

    # 2. Summarize each article via Gemini
    summarized = []
    for art in raw_articles[:6]:   # cap at 6 to stay under Gemini's free RPM limit
        prompt = f"""Summarize this AI news article in JSON with keys:
"headline" (max 10 words), "bulletPoints" (array of 3 strings), "whyItMatters" (1-2 sentences), "category" (one of: LLMs, Robotics, Startups, Ethics, Research, Tools, Other).
Return ONLY the JSON object, no markdown fences, no extra text.

Title: {art['title']}
Content: {art['content']}"""
        try:
            text = gemini(prompt)
            text = text.replace("```json", "").replace("```", "").strip()
            summary = json.loads(text)
            summarized.append({
                **summary,
                "sourceUrl":   art["link"],
                "sourceName":  art["source"],
                "publishedAt": art["pubDate"],
            })
        except Exception as e:
            print(f"Summarize error: {e}")

    if not summarized:
        return jsonify({"success": False, "error": "Failed to summarize any articles — both Gemini and Groq unavailable"}), 500
    print(f"[Newsletter] Summarized {len(summarized)}/{len(raw_articles[:6])} articles successfully")

    # 3. Generate daily insight via Gemini
    headlines = "\n".join([a.get("headline", "") for a in summarized])
    insight_prompt = f"""Based on these AI headlines, write one short insightful trend observation in exactly 2 sentences. No quotes. Just plain text.

Headlines:
{headlines}"""
    try:
        insight = gemini(insight_prompt)
    except Exception:
        insight = "AI continues to advance rapidly across multiple domains today."

    # 4. Save newsletter
    nl_id  = datetime.now().strftime("%Y%m%d_%H%M%S")
    nl_date = datetime.now().strftime("%Y-%m-%d")
    newsletter = {
        "id":       nl_id,
        "date":     nl_date,
        "insight":  insight,
        "articles": summarized,
        "createdAt": datetime.now().isoformat(),
    }
    path = os.path.join(AI_DAILY_DIR, f"nl_{nl_id}.json")
    with open(path, "w") as f:
        json.dump(newsletter, f, indent=2)

    # 5. Broadcast to all subscribers
    broadcast_count = 0
    broadcast_errors = []
    try:
        import smtplib, ssl
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        email_user = os.getenv("EMAIL_USER") or os.getenv("SMTP_USER", "")
        email_pass = os.getenv("EMAIL_PASS") or os.getenv("SMTP_PASS", "")

        if email_user and email_pass:
            subs_path = os.path.join(AI_DAILY_DIR, "subscriptions.json")
            subs = []
            if os.path.exists(subs_path):
                with open(subs_path) as f:
                    try: subs = json.load(f)
                    except: subs = []

            if subs:
                # Build article rows — filter per subscriber topics if set
                def build_article_rows(articles, sub_topics):
                    rows = ""
                    for art in articles:
                        cat = art.get("category", "")
                        # Show all articles if subscriber picked nothing, else filter
                        if sub_topics and cat and cat not in sub_topics:
                            continue
                        bullets = "".join(
                            f'<li style="margin-bottom:5px;color:#a1a1aa;font-size:13px;line-height:1.6">{b}</li>'
                            for b in art.get("bulletPoints", [])
                        )
                        rows += f"""
                        <div style="border:1px solid #27272a;border-radius:12px;padding:20px 24px;margin-bottom:16px;background:#18181b;">
                          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                            <span style="font-size:10px;font-family:monospace;letter-spacing:.12em;text-transform:uppercase;color:#52525b;background:#27272a;padding:3px 8px;border-radius:4px">{cat}</span>
                            <span style="font-size:10px;color:#52525b">{art.get('sourceName','')}</span>
                          </div>
                          <div style="font-size:15px;font-weight:700;color:#f4f4f5;margin-bottom:10px;line-height:1.4">{art.get('headline','')}</div>
                          <ul style="margin:0 0 10px;padding-left:18px">{bullets}</ul>
                          <div style="font-size:12px;color:#71717a;font-style:italic;margin-bottom:10px">{art.get('whyItMatters','')}</div>
                          <a href="{art.get('sourceUrl','#')}" style="font-size:12px;color:#22d3ee;text-decoration:none">Read full article →</a>
                        </div>"""
                    return rows or "<p style='color:#71717a;font-size:13px'>No articles matched your topics today.</p>"

                ssl_ctx = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl_ctx) as server:
                    server.login(email_user, email_pass)
                    for sub in subs:
                        sub_email  = sub.get("email", "")
                        sub_topics = sub.get("topics", [])
                        if not sub_email:
                            continue
                        try:
                            article_rows = build_article_rows(summarized, sub_topics)
                            topics_label = ", ".join(sub_topics) if sub_topics else "All Topics"
                            html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0f;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#0a0a0f;border-radius:16px;overflow:hidden;border:1px solid #27272a;">
        <tr><td style="padding:32px 40px 24px;border-bottom:1px solid #27272a;">
          <div style="display:inline-block;background:#27272a;border-radius:8px;padding:5px 12px;margin-bottom:14px;">
            <span style="font-family:monospace;font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:#71717a;">AI DAILY · {nl_date}</span>
          </div>
          <h1 style="margin:0;font-size:26px;font-weight:800;color:#f4f4f5;letter-spacing:-.02em;line-height:1.15">
            Today's AI Digest 🤖
          </h1>
          <p style="margin:10px 0 0;font-size:13px;color:#71717a;">{insight}</p>
        </td></tr>
        <tr><td style="padding:28px 40px;">
          <p style="margin:0 0 6px;font-size:10px;font-family:monospace;letter-spacing:.14em;text-transform:uppercase;color:#52525b;">YOUR TOPICS: {topics_label}</p>
          <p style="margin:0 0 20px;font-size:10px;font-family:monospace;letter-spacing:.14em;text-transform:uppercase;color:#52525b;">{len(summarized)} ARTICLES TODAY</p>
          {article_rows}
        </td></tr>
        <tr><td style="padding:20px 40px;border-top:1px solid #27272a;">
          <p style="margin:0;font-size:11px;color:#3f3f46;text-align:center;">
            You're receiving this because you subscribed with {sub_email} · AI Daily by Student Platform
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
                            msg = MIMEMultipart("alternative")
                            msg["Subject"] = f"🤖 AI Daily — {nl_date} Edition ({len(summarized)} stories)"
                            msg["From"]    = f"AI Daily <{email_user}>"
                            msg["To"]      = sub_email
                            msg.attach(MIMEText(html_body, "html"))
                            server.sendmail(email_user, sub_email, msg.as_string())
                            broadcast_count += 1
                            print(f"[Newsletter] Sent edition to {sub_email}")
                        except Exception as sub_err:
                            broadcast_errors.append(sub_email)
                            print(f"[Newsletter] Failed to send to {sub_email}: {sub_err}")
        else:
            print("[Newsletter] EMAIL_USER/EMAIL_PASS not set — skipping broadcast")
    except Exception as broadcast_err:
        print(f"[Newsletter] Broadcast error: {broadcast_err}")

    return jsonify({
        "success": True,
        "newsletter": newsletter,
        "broadcast": {
            "sent": broadcast_count,
            "failed": len(broadcast_errors),
            "skipped_emails": broadcast_errors
        }
    })


@app.route("/api/ai-daily/subscribe", methods=["POST"])
def api_ai_daily_subscribe():
    """Save email subscription and send welcome email."""
    body   = request.get_json(force=True)
    email  = (body.get("email") or "").strip()
    topics = body.get("topics", [])
    if not email or "@" not in email:
        return jsonify({"success": False, "error": "Invalid email"}), 400

    subs_path = os.path.join(AI_DAILY_DIR, "subscriptions.json")
    subs = []
    if os.path.exists(subs_path):
        with open(subs_path) as f:
            try: subs = json.load(f)
            except: subs = []

    is_new = not any(s.get("email") == email for s in subs)
    email_status = "not_attempted"

    if is_new:
        subs.append({"email": email, "topics": topics, "subscribedAt": datetime.now().isoformat()})
        with open(subs_path, "w") as f:
            json.dump(subs, f, indent=2)

        # ── Send welcome email ──────────────────────────────
        try:
            import smtplib, ssl
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            email_user = os.getenv("EMAIL_USER") or os.getenv("SMTP_USER", "")
            email_pass = os.getenv("EMAIL_PASS") or os.getenv("SMTP_PASS", "")

            print(f"[Email Debug] EMAIL_USER set: {bool(email_user)}, EMAIL_PASS set: {bool(email_pass)}")

            if not email_user or not email_pass:
                email_status = "skipped_no_credentials"
                print("[Newsletter] EMAIL_USER / EMAIL_PASS not set — skipping welcome email")
            else:
                topics_str = ", ".join(topics) if topics else "All Topics"
                html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0f;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#18181b;border-radius:16px;overflow:hidden;border:1px solid #27272a;">
        <tr><td style="background:#0a0a0f;padding:32px 40px 24px;border-bottom:1px solid #27272a;">
          <div style="display:inline-block;background:#27272a;border-radius:8px;padding:6px 14px;margin-bottom:16px;">
            <span style="font-family:monospace;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#71717a;">AI DAILY</span>
          </div>
          <h1 style="margin:0;font-size:28px;font-weight:800;color:#f4f4f5;letter-spacing:-.03em;line-height:1.1;">
            You're in. 🎉
          </h1>
          <p style="margin:10px 0 0;font-size:14px;color:#71717a;line-height:1.6;">
            Welcome to AI Daily — your edge on everything happening in artificial intelligence.
          </p>
        </td></tr>
        <tr><td style="padding:32px 40px;">
          <p style="margin:0 0 20px;font-size:15px;color:#a1a1aa;line-height:1.7;">
            Hey there 👋,<br><br>
            You've subscribed to <strong style="color:#f4f4f5;">AI Daily</strong>. Every day we'll send you the sharpest AI news, research, and tools — curated and summarised so you stay ahead without the noise.
          </p>
          <div style="background:#0a0a0f;border:1px solid #27272a;border-radius:10px;padding:20px 24px;margin-bottom:24px;">
            <div style="font-family:monospace;font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:#52525b;margin-bottom:12px;">YOUR TOPICS</div>
            <div style="font-size:14px;color:#22d3ee;font-weight:600;">{topics_str}</div>
          </div>
          <p style="margin:0 0 8px;font-size:12px;font-family:monospace;letter-spacing:.12em;text-transform:uppercase;color:#52525b;">WHAT TO EXPECT</p>
          <ul style="margin:0 0 24px;padding-left:20px;color:#a1a1aa;font-size:14px;line-height:1.8;">
            <li>Daily AI news briefs, straight to your inbox</li>
            <li>Research summaries from top labs</li>
            <li>New tools &amp; product launches</li>
            <li>No spam, unsubscribe anytime</li>
          </ul>
          <p style="margin:0;font-size:14px;color:#71717a;">
            See you in your inbox,<br>
            <strong style="color:#f4f4f5;">The AI Daily Team</strong>
          </p>
        </td></tr>
        <tr><td style="padding:20px 40px;border-top:1px solid #27272a;background:#0a0a0f;">
          <p style="margin:0;font-size:11px;color:#3f3f46;text-align:center;">
            You subscribed with {email} · AI Daily by Student Platform
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

                msg = MIMEMultipart("alternative")
                msg["Subject"] = "🎉 Welcome to AI Daily — You're subscribed!"
                msg["From"]    = f"AI Daily <{email_user}>"
                msg["To"]      = email
                msg.attach(MIMEText(html_body, "html"))

                print(f"[Email Debug] Connecting to smtp.gmail.com:465 ...")
                ssl_ctx = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl_ctx) as server:
                    print(f"[Email Debug] Logging in as {email_user} ...")
                    server.login(email_user, email_pass)
                    print(f"[Email Debug] Sending to {email} ...")
                    server.sendmail(email_user, email, msg.as_string())
                print(f"[Email Debug] ✅ Welcome email sent to {email}")
                email_status = "sent"

        except Exception as mail_err:
            email_status = f"error: {str(mail_err)}"
            print(f"[Email Debug] ❌ Email send failed: {mail_err}")

    return jsonify({"success": True, "is_new": is_new, "email_status": email_status})


@app.route("/api/ai-daily/test-email", methods=["POST"])
def api_test_email():
    """Debug endpoint — tests email credentials directly. Remove after confirming it works."""
    import smtplib, ssl
    from email.mime.text import MIMEText

    email_user = os.getenv("EMAIL_USER") or os.getenv("SMTP_USER", "")
    email_pass = os.getenv("EMAIL_PASS") or os.getenv("SMTP_PASS", "")
    to_email   = (request.get_json(force=True) or {}).get("email", email_user)

    if not email_user or not email_pass:
        return jsonify({
            "success": False,
            "error": "EMAIL_USER or EMAIL_PASS not set in environment",
            "EMAIL_USER_set": bool(email_user),
            "EMAIL_PASS_set": bool(email_pass),
        })

    try:
        msg = MIMEText("<h1>Test email from AI Daily ✅</h1><p>Email is working correctly!</p>", "html")
        msg["Subject"] = "AI Daily — Email Test"
        msg["From"]    = f"AI Daily <{email_user}>"
        msg["To"]      = to_email

        ssl_ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl_ctx) as server:
            server.login(email_user, email_pass)
            server.sendmail(email_user, to_email, msg.as_string())

        return jsonify({"success": True, "message": f"Test email sent to {to_email}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "type": type(e).__name__})
if __name__ == "__main__":
    if not os.getenv("GROQ_API_KEY"):
        print("\n⚠️  GROQ_API_KEY not set in .env!")
        print("   Get free key → https://console.groq.com\n")
    else:
        print("\n✅ Groq API key loaded!")

    os.makedirs("output", exist_ok=True)
    print("🎓  Student Opportunity Finder →  http://localhost:5000\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)