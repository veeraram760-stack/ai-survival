import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("ai_survival.quality")


class QualityController:
    @staticmethod
    async def validate(db: AsyncSession, task_id: str, result: Dict[str, Any], expected: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        checks = {
            "completeness": QualityController._check_completeness(result, expected),
            "accuracy": QualityController._check_accuracy(result),
            "format": QualityController._check_format(result),
            "duplication": QualityController._check_duplication(db, task_id, result),
            "validity": QualityController._check_validity(result),
        }
        passed = all(checks.values())
        return {
            "passed": passed,
            "checks": checks,
            "score": sum(1 for v in checks.values() if v) / len(checks) * 100,
        }

    @staticmethod
    def _check_completeness(result: Dict[str, Any], expected: Optional[Dict[str, Any]]) -> bool:
        if not expected:
            return bool(result)
        for key in expected:
            if key not in result:
                return False
        return True

    @staticmethod
    def _check_accuracy(result: Dict[str, Any]) -> bool:
        if not isinstance(result, dict):
            return False
        status = result.get("status")
        if status and status not in ("success", "partial", "failed"):
            return False
        return True

    @staticmethod
    def _check_format(result: Dict[str, Any]) -> bool:
        return isinstance(result, dict)

    @staticmethod
    async def _check_duplication(db: AsyncSession, task_id: str, result: Dict[str, Any]) -> bool:
        return True

    @staticmethod
    def _check_validity(result: Dict[str, Any]) -> bool:
        if result.get("status") == "failed":
            return "error" in result or "reason" in result
        return True

    @staticmethod
    def validate_output_format(agent_name: str, task_id: str, status: str, summary: str, result: Any, confidence: float, issues: str, recommendation: str, next_action: str) -> Dict[str, Any]:
        return {
            "agent_name": agent_name,
            "task_id": task_id,
            "status": status,
            "summary": summary,
            "result": result,
            "confidence": confidence,
            "issues": issues,
            "recommendation": recommendation,
            "next_action": next_action,
        }
