import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>'))

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_table_borders(table, color="D3D3D3"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="single" w:sz="4" w:space="0" w:color="{color}"/>
            <w:bottom w:val="single" w:sz="6" w:space="0" w:color="1F4E79"/>
            <w:left w:val="none"/>
            <w:right w:val="none"/>
            <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{color}"/>
            <w:insideV w:val="none"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)

def build_document(output_path):
    doc = Document()
    
    # Page setup - 0.75 in margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)
        
    # Styles
    COLOR_PRIMARY = RGBColor(31, 78, 121)    # Deep Navy
    COLOR_SECONDARY = RGBColor(46, 117, 182) # Blue
    COLOR_DARK = RGBColor(38, 38, 38)        # Charcoal
    COLOR_MUTED = RGBColor(89, 89, 89)       # Slate Gray
    COLOR_ACCENT = RGBColor(192, 0, 0)       # Brick Red
    COLOR_SUCCESS = RGBColor(34, 139, 34)    # Forest Green

    # Base style
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Calibri'
    style_normal.font.size = Pt(10.5)
    style_normal.font.color.rgb = COLOR_DARK
    style_normal.paragraph_format.line_spacing = 1.15
    style_normal.paragraph_format.space_after = Pt(4)

    # ---------------- HEADER & TITLE ----------------
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(2)
    run_title = title_p.add_run("SolarSense EMS")
    run_title.font.size = Pt(24)
    run_title.font.bold = True
    run_title.font.color.rgb = COLOR_PRIMARY

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_after = Pt(12)
    run_sub = sub_p.add_run("Master Sprint Plan & Project Audit — Milestone 4 to Milestone 5")
    run_sub.font.size = Pt(13)
    run_sub.font.color.rgb = COLOR_SECONDARY
    run_sub.font.bold = True

    # Metadata Box
    meta_table = doc.add_table(rows=2, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_table.autofit = False
    set_table_borders(meta_table, "BDD7EE")
    
    meta_data = [
        [("Sprint Timeline:", " October 19 – October 25, 2026"), ("Academic Alignment:", " 1.5 Weeks Ahead of Outline")],
        [("Team Allocation:", " Abubakar (Lead) | Zaeem (Vision)"), ("Fast-Track Goal:", " Complete 8-Week Scope in 1 Month")]
    ]
    for r_idx, row in enumerate(meta_data):
        for c_idx, (bold_txt, regular_txt) in enumerate(row):
            cell = meta_table.cell(r_idx, c_idx)
            set_cell_background(cell, "F2F4F8")
            set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r1 = p.add_run(bold_txt)
            r1.bold = True
            r1.font.size = Pt(9.5)
            r1.font.color.rgb = COLOR_PRIMARY
            r2 = p.add_run(regular_txt)
            r2.font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ---------------- SECTION 1 ----------------
    h1 = doc.add_paragraph()
    h1.paragraph_format.space_before = Pt(14)
    h1.paragraph_format.space_after = Pt(4)
    r_h1 = h1.add_run("1. Executive Standing & Course Milestone Alignment")
    r_h1.font.size = Pt(14)
    r_h1.font.bold = True
    r_h1.font.color.rgb = COLOR_PRIMARY

    p_intro = doc.add_paragraph()
    p_intro.add_run(
        "According to the official project course outline, the academic class is currently at "
    )
    r_w3 = p_intro.add_run("Week 3 (Requirements, Data & System Design)")
    r_w3.bold = True
    p_intro.add_run(
        ". To fulfill the team's core strategy of remaining strictly 1 to 2 weeks ahead and graduating the 8-week project within "
    )
    r_4w = p_intro.add_run("4 weeks (1 month)")
    r_4w.bold = True
    p_intro.add_run(
        ", the SolarSense team is already situated at the boundary of Week 4 and Week 5."
    )

    # Fast Track Table
    ft_table = doc.add_table(rows=5, cols=3)
    ft_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(ft_table, "D9D9D9")
    
    headers = ["Calendar Period", "University Course Milestone", "SolarSense Sprint Execution Target"]
    for i, title in enumerate(headers):
        cell = ft_table.cell(0, i)
        set_cell_background(cell, "1F4E79")
        set_cell_margins(cell, top=100, bottom=100, left=100, right=100)
        p = cell.paragraphs[0]
        r = p.add_run(title)
        r.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    ft_rows = [
        ("Oct 19 – Oct 25", "Week 3: System Design & Specs", "WEEK 4/5: Close Backend & Train AI Models (CURRENT SPRINT)"),
        ("Oct 26 – Nov 01", "Week 4: Data & Backend Foundation", "WEEK 5/6: Multi-Agent Logic & MILP Battery Optimizer"),
        ("Nov 02 – Nov 08", "Week 5: AI & Agent Development", "WEEK 6/7: Full Streamlit Web UI Application"),
        ("Nov 09 – Nov 15", "Week 6–8: Integration & Final Demos", "WEEK 7/8: System Benchmark Evaluation & Final Defense")
    ]
    for r_idx, row in enumerate(ft_rows, start=1):
        bg = "FFFFFF" if r_idx % 2 == 1 else "F9FBFD"
        if r_idx == 1:
            bg = "EBF1F5"  # Highlight current sprint
        for c_idx, val in enumerate(row):
            cell = ft_table.cell(r_idx, c_idx)
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=70, bottom=70, left=100, right=100)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val)
            r.font.size = Pt(9.5)
            if r_idx == 1:
                r.bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # ---------------- SECTION 2 ----------------
    h2 = doc.add_paragraph()
    h2.paragraph_format.space_before = Pt(12)
    h2.paragraph_format.space_after = Pt(4)
    r_h2 = h2.add_run("2. Deep Technical Audit: What is Done vs. What is NOT Done")
    r_h2.font.size = Pt(14)
    r_h2.font.bold = True
    r_h2.font.color.rgb = COLOR_PRIMARY

    # Sub 2.1
    p_done_h = doc.add_paragraph()
    r = p_done_h.add_run("A. Completed Components & Verified Assets (Done)")
    r.bold = True
    r.font.color.rgb = COLOR_SUCCESS

    done_items = [
        ("Gold-Tier Master Feature Store: ", "Created data/processed/master_ems_timeseries.csv containing 11,136 continuous hourly rows across 464 historical days. Ingested 5-minute inverter telemetry, satellite weather, synthetic 2-shift factory load (200–450 kW), and grid outage flags."),
        ("Physics-Based Soiling Model: ", "Implemented src/soiling/calibrate_soiling_model.py anchored to the verified 2026-09-23 panel wash date. Incorporates Perez POA irradiance and SAPM temperature derates. Validated 170 days of severe soiling loss with CUSUM change-point detection."),
        ("NEPRA / LESCO Tariff Engine: ", "Implemented src/optimizer/tariff_engine.py with official B3 industrial rates (60 PKR peak, 38 PKR off-peak), MDI threshold (1,200 PKR/kW over 500 kW), and diesel backup costs (95 PKR/kWh). Validated historical baseline penalty of 2.36 Million PKR."),
        ("Structured Defect Image Dataset: ", "Ingested and structured Dataset A in data/processed/panel_images/solarsense_hybrid_v1/ across 5 distinct classes (clean, dusty, bird_drop, electrical_damage, physical_damage) with clean train, val, and test splits."),
        ("Image Verification Protocol: ", "Wrote and executed src/vision/verify_dataset_a.py to eliminate corrupt images, verify duplicate hashes (SHA-256), and ensure zero cross-split leakage."),
        ("Project Governance & Pitch Decks: ", "Established clean GitHub repository (Abubakar651/SolarSense-Ems), comprehensive README.md, pitch decks (SolarSense_Industrial_EMS.pptx & Pitch_Deck2.pptx), and multi-agent architecture in docs/agents.md.")
    ]
    for b_title, b_desc in done_items:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(2)
        r_b = bp.add_run(b_title)
        r_b.bold = True
        r_b.font.color.rgb = COLOR_PRIMARY
        bp.add_run(b_desc)

    # Sub 2.2
    p_not_done_h = doc.add_paragraph()
    p_not_done_h.paragraph_format.space_before = Pt(6)
    r = p_not_done_h.add_run("B. Outstanding Gaps to Close (NOT Done Yet)")
    r.bold = True
    r.font.color.rgb = COLOR_ACCENT

    not_done_items = [
        ("Core AI Model Training: ", "LightGBM solar forecasting model (src/forecast/train_solar_pv.py) and EfficientNet-B2 defect classifier (src/vision/train_classifier.py) have not yet been trained or serialized."),
        ("Battery Dispatch Optimizer: ", "Mixed-Integer Linear Programming (MILP) scheduler in PuLP (src/optimizer/battery_scheduler.py) is missing, leaving battery dispatch un-automated."),
        ("Automated Test Suite: ", "The tests/ directory is completely empty; automated unit tests for data integrity and tariff penalty triggers are required for Milestone 4 validation."),
        ("Exploratory Data Analysis Notebook: ", "The notebooks/ directory is completely empty; a clean, reproducible Jupyter notebook visualizing the 2.36 Million PKR MDI penalty spikes is needed."),
        ("Reusable Backend Access Layer: ", "No object-oriented Python loader (EMSDataStore) currently exists to feed 24-hour simulation windows to the models and the upcoming UI.")
    ]
    for b_title, b_desc in not_done_items:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(2)
        r_b = bp.add_run(b_title)
        r_b.bold = True
        r_b.font.color.rgb = COLOR_ACCENT
        bp.add_run(b_desc)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # ---------------- SECTION 3 ----------------
    h3 = doc.add_paragraph()
    h3.paragraph_format.space_before = Pt(12)
    h3.paragraph_format.space_after = Pt(4)
    r_h3 = h3.add_run("3. Team Workstream Division: Abubakar vs. Zaeem")
    r_h3.font.size = Pt(14)
    r_h3.font.bold = True
    r_h3.font.color.rgb = COLOR_PRIMARY

    p_div = doc.add_paragraph()
    p_div.add_run(
        "To ensure parallel velocity without merge bottlenecks, responsibilities are divided cleanly by technical domain:"
    )

    team_table = doc.add_table(rows=6, cols=2)
    team_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(team_table, "D9D9D9")

    # Header
    for idx, (col_name, user_role) in enumerate([("Abubakar (Lead)", "Systems, Time-Series & Optimization"), ("Zaeem (Member 2)", "Computer Vision & Industrial Load EDA")]):
        cell = team_table.cell(0, idx)
        set_cell_background(cell, "1F4E79")
        set_cell_margins(cell, top=100, bottom=100, left=100, right=100)
        p = cell.paragraphs[0]
        r1 = p.add_run(f"{col_name}\n")
        r1.bold = True
        r1.font.size = Pt(10)
        r1.font.color.rgb = RGBColor(255, 255, 255)
        r2 = p.add_run(user_role)
        r2.font.size = Pt(8.5)
        r2.font.italic = True
        r2.font.color.rgb = RGBColor(220, 230, 242)

    team_tasks = [
        ("Backend Data Store: src/data_engineering/feature_store.py", "PyTorch DataLoader: src/vision/dataloader.py"),
        ("Automated Tests: tests/test_data_integrity.py", "Load EDA Notebook: notebooks/01_industrial_load_eda.ipynb"),
        ("Solar PV Model: src/forecast/train_solar_pv.py (LightGBM)", "Defect Classifier: src/vision/train_classifier.py (EfficientNet)"),
        ("Battery Dispatch: src/optimizer/battery_scheduler.py (MILP)", "Vision Evaluation: src/vision/evaluate_classifier.py (Matrix)"),
        ("Outage Classifier: src/grid_outage/predict_outage.py", "Dataset A Documentation: docs/dataset_A_audit_report.md")
    ]
    for r_idx, (t_abu, t_zae) in enumerate(team_tasks, start=1):
        bg = "FFFFFF" if r_idx % 2 == 1 else "F9FBFD"
        c0 = team_table.cell(r_idx, 0)
        c1 = team_table.cell(r_idx, 1)
        for c, text in [(c0, t_abu), (c1, t_zae)]:
            set_cell_background(c, bg)
            set_cell_margins(c, top=70, bottom=70, left=100, right=100)
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.add_run(text).font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # ---------------- SECTION 4 ----------------
    h4 = doc.add_paragraph()
    h4.paragraph_format.space_before = Pt(12)
    h4.paragraph_format.space_after = Pt(4)
    r_h4 = h4.add_run("4. Day-by-Day Sprint Schedule with Strict Deadlines")
    r_h4.font.size = Pt(14)
    r_h4.font.bold = True
    r_h4.font.color.rgb = COLOR_PRIMARY

    schedule_data = [
        ("Monday, Oct 19 (23:59)", "Foundation & Data Loaders",
         "Implement EMSDataStore class in src/data_engineering/feature_store.py to provide get_day_slice(date) and get_tariff_window(date).",
         "Implement PyTorch DataLoader in src/vision/dataloader.py with 260x260 transforms, flips, and normalization."),
        
        ("Tuesday, Oct 20 (23:59)", "Unit Tests & Load Analysis",
         "Create tests/test_data_integrity.py and tests/test_tariff_engine.py. Ensure 100% pytest pass rate with zero NaN values.",
         "Create notebooks/01_industrial_load_eda.ipynb. Plot shift profiles and visualize the 2.36 Million PKR MDI penalty spikes."),
        
        ("Wednesday, Oct 21 (23:59)", "Core Model Training",
         "Train LightGBM solar generation model (src/forecast/train_solar_pv.py) targeting R² >= 0.90. Save models/solar_pv_lightgbm.pkl.",
         "Train EfficientNet-B2 defect classifier (src/vision/train_classifier.py) on solarsense_hybrid_v1. Save models/efficientnet_b2_defects.pth."),
        
        ("Thursday, Oct 22 (23:59)", "Optimization & Vision Metrics",
         "Implement MILP battery dispatch in src/optimizer/battery_scheduler.py using PuLP to minimize electricity, penalty, and diesel costs.",
         "Implement src/vision/evaluate_classifier.py. Export confusion matrix graphic to docs/samples/confusion_matrix_efficientnet.png."),
        
        ("Friday, Oct 23 (23:59)", "Outage Model & Benchmarks",
         "Train Random Forest blackout probability classifier in src/grid_outage/predict_outage.py. Connect to battery outage buffer.",
         "Create notebooks/02_model_performance_benchmarks.ipynb compiling performance metrics across all models."),
        
        ("Saturday, Oct 24 (18:00)", "Git PRs & Code Integration",
         "Review Zaeem's PRs, verify test suite execution, and merge feature branches into main.",
         "Submit PRs, verify docstrings, and update docs/dataset_A_audit_report.md."),
        
        ("Sunday, Oct 25 (20:00)", "Sprint Retrospective & Release",
         "Audit acceptance criteria, tag Git release v0.5.0-milestone5, and conduct Week 6 Streamlit UI planning sync.",
         "Audit acceptance criteria, participate in retrospective, and align on Streamlit UI wireframes.")
    ]

    sched_table = doc.add_table(rows=8, cols=4)
    sched_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(sched_table, "D9D9D9")

    # Header
    sched_headers = ["Day & Deadline", "Sprint Milestone", "Abubakar Deliverable", "Zaeem Deliverable"]
    for i, title in enumerate(sched_headers):
        cell = sched_table.cell(0, i)
        set_cell_background(cell, "1F4E79")
        set_cell_margins(cell, top=100, bottom=100, left=80, right=80)
        p = cell.paragraphs[0]
        r = p.add_run(title)
        r.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    for r_idx, (day, ms, abu, zae) in enumerate(schedule_data, start=1):
        bg = "FFFFFF" if r_idx % 2 == 1 else "F9FBFD"
        for c_idx, val in enumerate([day, ms, abu, zae]):
            cell = sched_table.cell(r_idx, c_idx)
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=70, bottom=70, left=80, right=80)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if c_idx == 0:
                r.bold = True
                r.font.color.rgb = COLOR_PRIMARY
            elif c_idx == 1:
                r.bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # ---------------- SECTION 5 ----------------
    h5 = doc.add_paragraph()
    h5.paragraph_format.space_before = Pt(12)
    h5.paragraph_format.space_after = Pt(4)
    r_h5 = h5.add_run("5. Quantitative Acceptance Criteria (Sunday Night Audit)")
    r_h5.font.size = Pt(14)
    r_h5.font.bold = True
    r_h5.font.color.rgb = COLOR_PRIMARY

    crit_table = doc.add_table(rows=7, cols=3)
    crit_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(crit_table, "D9D9D9")

    crit_headers = ["Component", "Quantitative Target", "Verification Command / Method"]
    for i, title in enumerate(crit_headers):
        cell = crit_table.cell(0, i)
        set_cell_background(cell, "1F4E79")
        set_cell_margins(cell, top=100, bottom=100, left=100, right=100)
        p = cell.paragraphs[0]
        r = p.add_run(title)
        r.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    crit_rows = [
        ("Data Store & Tests", "100% passing pytest assertions with zero data leakage", "pytest tests/ -v"),
        ("Solar PV Forecast Model", "R² >= 0.90, RMSE <= 0.45 kW on holdout test set", "python3 src/forecast/train_solar_pv.py"),
        ("Panel Defect Classifier", "Overall Test Accuracy >= 94%, Macro F1 >= 0.92", "python3 src/vision/evaluate_classifier.py"),
        ("Battery Dispatch Optimizer", "Eliminates 100% of MDI violations; solve time < 1 sec", "python3 src/optimizer/battery_scheduler.py"),
        ("Exploratory Notebook", "Reproducible run visualizing the 2.36 Million PKR penalty", "notebooks/01_industrial_load_eda.ipynb"),
        ("Version Control", "Clean Git commit history, 0 merge conflicts, tagged v0.5.0", "git status && git log -n 5")
    ]
    for r_idx, row in enumerate(crit_rows, start=1):
        bg = "FFFFFF" if r_idx % 2 == 1 else "F9FBFD"
        for c_idx, val in enumerate(row):
            cell = crit_table.cell(r_idx, c_idx)
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=70, bottom=70, left=100, right=100)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val)
            r.font.size = Pt(9.0)
            if c_idx == 0:
                r.bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # ---------------- SECTION 6 ----------------
    h6 = doc.add_paragraph()
    h6.paragraph_format.space_before = Pt(12)
    h6.paragraph_format.space_after = Pt(4)
    r_h6 = h6.add_run("6. Execution Commands Reference")
    r_h6.font.size = Pt(14)
    r_h6.font.bold = True
    r_h6.font.color.rgb = COLOR_PRIMARY

    p_cmd = doc.add_paragraph()
    p_cmd.add_run("Team members can verify and run their modules using the following CLI standard commands:")

    cmd_box = doc.add_table(rows=1, cols=1)
    cmd_box.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_cell_background(cmd_box.cell(0, 0), "F2F4F7")
    set_table_borders(cmd_box, "B0C4DE")
    set_cell_margins(cmd_box.cell(0, 0), top=120, bottom=120, left=150, right=150)
    
    cp = cmd_box.cell(0, 0).paragraphs[0]
    commands_text = (
        "# 1. Run Automated Test Suite\n"
        "pytest tests/ -v\n\n"
        "# 2. Train Solar PV Forecasting Model (LightGBM)\n"
        "python3 src/forecast/train_solar_pv.py\n\n"
        "# 3. Train Panel Defect Classifier (EfficientNet-B2)\n"
        "python3 src/vision/train_classifier.py\n\n"
        "# 4. Evaluate Vision Model & Generate Confusion Matrix\n"
        "python3 src/vision/evaluate_classifier.py\n\n"
        "# 5. Run 24-Hour MILP Battery Optimization Simulation\n"
        "python3 src/optimizer/battery_scheduler.py"
    )
    for line in commands_text.split('\n'):
        if line.startswith('#'):
            r = cp.add_run(line + '\n')
            r.font.name = 'Consolas'
            r.font.size = Pt(9)
            r.font.color.rgb = COLOR_MUTED
            r.font.bold = True
        else:
            r = cp.add_run(line + '\n')
            r.font.name = 'Consolas'
            r.font.size = Pt(9.5)
            r.font.color.rgb = COLOR_PRIMARY

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    print(f"Successfully generated DOCX at: {output_path}")

if __name__ == "__main__":
    out_file = "/home/bakar/Documents/Solar Sens EMS/docs/WEEK_4_5_SPRINT_PLAN_AND_AUDIT.docx"
    build_document(out_file)
