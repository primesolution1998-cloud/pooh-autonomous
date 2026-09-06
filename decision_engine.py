import os
import json
import logging

logger = logging.getLogger("Pooh-DecisionEngine")

class PoohCOOEngine:
    def __init__(self):
        self.risk_threshold_cold = 200
        self.daily_safe_limit = 500

    def evaluate_campaign(self, recipient_count, is_cold_list=True):
        logger.info(f"Evaluating strategy for {recipient_count} recipients.")
        
        if recipient_count > self.risk_threshold_cold and is_cold_list:
            selected_route = "META_CLOUD_API"
            strategy = "High volume cold list detected. Selecting Official Cloud API to eliminate ban risk."
            batch_size = 250
            delay_sec = 5
        else:
            selected_route = "MAMMA_GATEWAY"
            strategy = "Low volume / rapid testing list. Deploying via Mamma Web Gateway with anti-ban delay."
            batch_size = 30
            delay_sec = 25

        decision_payload = {
            "route": selected_route,
            "strategy": strategy,
            "batch_size": batch_size,
            "delay_per_message_sec": delay_sec,
            "status": "APPROVED"
        }
        return decision_payload

    def generate_coo_report(self, decision):
        report = (
            f"🧠 *COO Autonomous Decision Executed*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *Route Selected:* `{decision['route']}`\n"
            f"📋 *Reasoning:* {decision['strategy']}\n"
            f"⚙️ *Throttle Profile:* Batch of {decision['batch_size']} | {decision['delay_per_message_sec']}s delays\n"
            f"🚀 *Engine Status:* Ready to Dispatch"
        )
        return report

coo_engine = PoohCOOEngine()
