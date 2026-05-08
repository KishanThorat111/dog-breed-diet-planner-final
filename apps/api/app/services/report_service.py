"""PDF report generator using ReportLab."""
from __future__ import annotations

import io
import logging
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.diet_plan import DietPlan
from app.models.pet import Pet

logger = logging.getLogger(__name__)

BRAND_COLOR = colors.HexColor("#6366F1")  # Indigo
ACCENT_COLOR = colors.HexColor("#F59E0B")  # Amber


def generate_diet_report_pdf(pet: Pet, plan: DietPlan) -> bytes:
    """
    Generate a professional PDF diet report.
    Returns raw PDF bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        textColor=BRAND_COLOR,
        fontSize=22,
        spaceAfter=4,
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        textColor=BRAND_COLOR,
        fontSize=13,
        spaceBefore=14,
        spaceAfter=4,
    )
    body_style = styles["BodyText"]
    body_style.fontSize = 10

    story = []

    # ─── Header ───
    story.append(Paragraph("🐾 Dog Breed Diet Planner", title_style))
    story.append(Paragraph("Personalized Nutrition Report", styles["Subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_COLOR))
    story.append(Spacer(1, 0.4 * cm))

    # ─── Pet Profile ───
    story.append(Paragraph("Pet Profile", heading_style))
    pet_data = [
        ["Name", pet.name or "—"],
        ["Breed", plan.breed],
        ["Age", _format_age(plan.age_months)],
        ["Weight", f"{plan.weight_kg} kg"],
        ["Activity Level", plan.activity_level.replace("_", " ").title()],
        ["Sex", (pet.sex or "Unknown").title()],
        ["Neutered/Spayed", "Yes" if pet.is_neutered else "No"],
    ]
    if pet.allergies:
        pet_data.append(["Allergies", ", ".join(pet.allergies)])
    if pet.health_conditions:
        pet_data.append(["Health Conditions", ", ".join(pet.health_conditions)])

    story.append(_make_table(pet_data))
    story.append(Spacer(1, 0.4 * cm))

    # ─── Daily Nutritional Targets ───
    story.append(Paragraph("Daily Nutritional Targets", heading_style))
    nutrition_data = [
        ["Metric", "Daily Requirement"],
        ["Total Calories", f"{plan.daily_calories} kcal"],
        ["Protein", f"{plan.protein_g} g"],
        ["Fat", f"{plan.fat_g} g"],
        ["Carbohydrates", f"{plan.carbs_g} g"],
        ["Meals per Day", str(plan.meals_per_day)],
    ]
    story.append(_make_table(nutrition_data, has_header=True))
    story.append(Spacer(1, 0.4 * cm))

    # ─── Food Recommendations ───
    story.append(Paragraph("Recommended Foods", heading_style))
    food_data = [["Food", "Amount (g)", "Category", "Notes"]]
    for food in plan.food_recommendations:
        food_data.append([
            food.get("name", ""),
            str(food.get("amount_g", "")),
            food.get("category", "").title(),
            food.get("notes", "") or "—",
        ])
    if len(food_data) > 1:
        story.append(_make_table(food_data, has_header=True))
    story.append(Spacer(1, 0.4 * cm))

    # ─── Feeding Schedule ───
    story.append(Paragraph("Feeding Schedule", heading_style))
    schedule_data = [["Meal", "Time", "Calories (kcal)", "Approx. Amount (g)"]]
    for meal in plan.feeding_schedule:
        schedule_data.append([
            meal.get("meal_name", ""),
            meal.get("time_suggestion", ""),
            str(meal.get("amount_kcal", "")),
            str(meal.get("amount_g", "")),
        ])
    if len(schedule_data) > 1:
        story.append(_make_table(schedule_data, has_header=True))
    story.append(Spacer(1, 0.4 * cm))

    # ─── Foods to Avoid ───
    story.append(Paragraph("Foods to Avoid", heading_style))
    for food in plan.foods_to_avoid:
        story.append(Paragraph(f"• {food}", body_style))
    story.append(Spacer(1, 0.4 * cm))

    # ─── Supplements ───
    if plan.supplement_flags:
        story.append(Paragraph("Supplement Recommendations", heading_style))
        for supp in plan.supplement_flags:
            story.append(Paragraph(f"• {supp}", body_style))
        story.append(Spacer(1, 0.4 * cm))

    # ─── Notes ───
    if plan.notes:
        story.append(Paragraph("Important Notes", heading_style))
        story.append(Paragraph(plan.notes, body_style))
        story.append(Spacer(1, 0.4 * cm))

    # ─── Disclaimer ───
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    disclaimer_style = ParagraphStyle(
        "Disclaimer", parent=styles["Normal"], fontSize=8, textColor=colors.grey
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "⚠️ This report is AI-generated for informational purposes only. "
        "It does not constitute veterinary advice. Always consult a licensed veterinarian "
        "before making significant dietary changes, especially for pets with health conditions.",
        disclaimer_style,
    ))

    doc.build(story)
    return buffer.getvalue()


def _format_age(months: int) -> str:
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''}"
    years = months // 12
    rem = months % 12
    if rem:
        return f"{years} year{'s' if years != 1 else ''} {rem} month{'s' if rem != 1 else ''}"
    return f"{years} year{'s' if years != 1 else ''}"


def _make_table(data: list[list], has_header: bool = False) -> Table:
    col_widths = None  # Auto
    t = Table(data, colWidths=col_widths, repeatRows=1 if has_header else 0)
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F8F8FF")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]
    if has_header:
        style_cmds.extend([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
        ])
    else:
        style_cmds.extend([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ])
    t.setStyle(TableStyle(style_cmds))
    return t
