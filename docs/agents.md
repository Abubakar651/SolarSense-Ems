# AI Agents Architecture (Phase 2)

As we move into **Week 5 (AI/Agent Development)**, the SolarSense EMS transitions from a static data pipeline into an active, multi-agent AI system. 

The architecture relies on a **Master Orchestrator Agent** that communicates with several highly specialized sub-agents. This modular approach ensures that financial optimization, physical maintenance, and diagnostic tasks are handled by dedicated models.

---

## 1. The Master Orchestrator Agent (LLM)
**Role:** The overarching intelligence and user interface.
*   **Function:** Acts as a "Chat with your Factory" interface. The factory manager can ask, *"Why was my bill so high yesterday?"* or *"Should I wash the panels today?"*
*   **Workflow:** The Orchestrator parses the user's intent, queries the specialized sub-agents or the Master Feature Store (SQL/Pandas), and synthesizes a human-readable advisory report.
*   **Model Type:** Large Language Model (e.g., Gemini 1.5 Pro / GPT-4o) equipped with function calling (Tool Use).

## 2. Specialized Sub-Agents

### 🤖 Sub-Agent A: The Peak Shaver (RL / Optimization)
**Role:** Battery Dispatch Controller.
*   **The Problem:** LESCO Peak electricity (18:00–22:00) costs 60 PKR/kWh, and exceeding the 500kW load limit costs 1,200 PKR/kW.
*   **Function:** This agent predicts the factory load for the next 24 hours. It solves an optimization problem to decide exactly when to charge the 5.12 kWh battery (during cheap solar hours) and exactly when to discharge it (to avoid peak rates and MDI penalties).
*   **Model Type:** Reinforcement Learning (PPO/SAC) or Mixed-Integer Linear Programming (MILP).

### 🧽 Sub-Agent B: The Maintenance Oracle (Physics-Informed)
**Role:** Soiling & Cleaning Analyst.
*   **The Problem:** Washing panels costs 15,000 PKR, but dust slowly drains daily revenue.
*   **Function:** Monitors the `cumulative_soiling_loss_pkr` column in the master dataset. It analyzes weather forecasts (is it going to rain heavily tomorrow?) and decides if a manual wash is mathematically profitable.
*   **Model Type:** Rule-based expert system combined with CUSUM anomaly detection.

### 👁️ Sub-Agent C: The Vision Inspector (Computer Vision)
**Role:** Hardware Health Diagnostician.
*   **The Problem:** Physical damage, bird droppings, or electrical hotspots degrade panel performance invisibly.
*   **Function:** Processes drone imagery or smartphone photos uploaded by the user. It classifies the image into one of 5 classes (Clean, Dusty, Bird Droppings, Physical Damage, Electrical Damage) and routes emergency repair alerts to the Orchestrator.
*   **Model Type:** Convolutional Neural Network (CNN) - e.g., ResNet50 or YOLOv8 trained on Dataset A.

---

## Agent Communication Flow (Example Scenario)

1. **Trigger:** Factory load suddenly spikes to 498 kW at 14:00.
2. **Action (Sub-Agent A):** Detects imminent MDI penalty. Immediately commands the battery to discharge 3 kW to absorb the spike, keeping the grid draw safely at 495 kW.
3. **Notification (Orchestrator):** Sends an alert to the manager: *"MDI penalty of 1,200 PKR avoided by deploying 3kW of battery reserves."*
