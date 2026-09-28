from datetime import date
from typing import Any

from app.database.connection import get_db_connection
from app.gateway.action_gateway import ActionGateway


class LabTool:
    """
    Tool layer for Lab Management.

    Read operations:
        - get_lab_orders()
        - get_lab_order()
        - get_lab_results()

    State-changing operations:
        - update_lab_order()
        - record_lab_result()

    All state-changing operations go through ActionGateway.
    """

    def __init__(self, action_gateway: ActionGateway | None = None) -> None:
        self.gateway = (
            action_gateway
            if action_gateway is not None
            else ActionGateway()
        )

    # ============================================================
    # READ: LAB ORDERS
    # ============================================================

    def get_lab_orders(
        self,
        patient_id: str | None = None,
        order_status: str | None = None,
        priority: str | None = None,
        department_id: int | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:

        query = """
            SELECT
                lo.lab_order_id,
                lo.patient_id,
                lo.doctor_id,
                lo.department_id,
                d.department_name,
                d.department_code,
                lo.encounter_id,
                lo.test_code,
                lo.test_name,
                lo.priority,
                lo.order_status,
                lo.ordered_at,
                lo.collected_at,
                lo.completed_at,
                lo.clinical_notes
            FROM lab_orders lo
            INNER JOIN departments d
                ON lo.department_id = d.department_id
            WHERE 1 = 1
        """

        params: list[Any] = []

        if patient_id:
            query += " AND lo.patient_id = %s"
            params.append(patient_id)

        if order_status:
            query += " AND lo.order_status = %s"
            params.append(order_status)

        if priority:
            query += " AND lo.priority = %s"
            params.append(priority)

        if department_id is not None:
            query += " AND lo.department_id = %s"
            params.append(department_id)

        query += """
            ORDER BY
                CASE lo.priority
                    WHEN 'STAT' THEN 1
                    WHEN 'URGENT' THEN 2
                    WHEN 'ROUTINE' THEN 3
                    ELSE 4
                END,
                lo.ordered_at DESC,
                lo.lab_order_id DESC
            LIMIT %s
        """

        params.append(limit)

        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

            cursor.close()

        return rows

    # ============================================================
    # READ: SINGLE LAB ORDER
    # ============================================================

    def get_lab_order(
        self,
        lab_order_id: int,
    ) -> dict[str, Any] | None:

        query = """
            SELECT
                lo.lab_order_id,
                lo.patient_id,
                lo.doctor_id,
                lo.department_id,
                d.department_name,
                d.department_code,
                lo.encounter_id,
                lo.test_code,
                lo.test_name,
                lo.priority,
                lo.order_status,
                lo.ordered_at,
                lo.collected_at,
                lo.completed_at,
                lo.clinical_notes
            FROM lab_orders lo
            INNER JOIN departments d
                ON lo.department_id = d.department_id
            WHERE lo.lab_order_id = %s
            LIMIT 1
        """

        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            cursor.execute(query, (lab_order_id,))
            row = cursor.fetchone()

            cursor.close()

        return row

    # ============================================================
    # READ: LAB RESULTS
    # ============================================================

    def get_lab_results(
        self,
        lab_order_id: int | None = None,
        patient_id: str | None = None,
        result_status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:

        query = """
            SELECT
                lr.lab_result_id,
                lr.lab_order_id,
                lr.patient_id,
                lr.test_name,
                lr.result_value,
                lr.numeric_value,
                lr.unit,
                lr.reference_range,
                lr.result_status,
                lr.performed_at,
                lr.verified_at,
                lr.verified_by_doctor_id,
                lr.interpretation
            FROM lab_results lr
            WHERE 1 = 1
        """

        params: list[Any] = []

        if lab_order_id is not None:
            query += " AND lr.lab_order_id = %s"
            params.append(lab_order_id)

        if patient_id:
            query += " AND lr.patient_id = %s"
            params.append(patient_id)

        if result_status:
            query += " AND lr.result_status = %s"
            params.append(result_status)

        query += """
            ORDER BY
                CASE lr.result_status
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'ABNORMAL' THEN 2
                    WHEN 'PENDING' THEN 3
                    WHEN 'NORMAL' THEN 4
                    ELSE 5
                END,
                lr.created_at DESC,
                lr.lab_result_id DESC
            LIMIT %s
        """

        params.append(limit)

        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

            cursor.close()

        return rows

    # ============================================================
    # ACTION: UPDATE LAB ORDER
    # ============================================================

    def update_lab_order(
        self,
        lab_order_id: int,
        new_status: str,
        requested_by_agent: str = "LabAgent",
    ) -> dict[str, Any]:

        gateway_request_id = self.gateway.create_request(
            action_type="UPDATE_LAB_ORDER",
            requested_by_agent=requested_by_agent,
            target_type="LAB_ORDER",
            target_id=str(lab_order_id),
            request_payload={
                "lab_order_id": lab_order_id,
                "new_status": new_status,
            },
        )

        return self.gateway.execute_action(gateway_request_id)

    # ============================================================
    # ACTION: RECORD LAB RESULT
    # ============================================================

    def record_lab_result(
        self,
        lab_order_id: int,
        patient_id: str,
        test_name: str,
        result_value: str | None = None,
        numeric_value: float | None = None,
        unit: str | None = None,
        reference_range: str | None = None,
        result_status: str = "PENDING",
        performed_at: Any = None,
        verified_by_doctor_id: int | None = None,
        interpretation: str | None = None,
        requested_by_agent: str = "LabAgent",
    ) -> dict[str, Any]:

        payload = {
            "lab_order_id": lab_order_id,
            "patient_id": patient_id,
            "test_name": test_name,
            "result_value": result_value,
            "numeric_value": numeric_value,
            "unit": unit,
            "reference_range": reference_range,
            "result_status": result_status,
            "performed_at": performed_at,
            "verified_by_doctor_id": verified_by_doctor_id,
            "interpretation": interpretation,
        }

        gateway_request_id = self.gateway.create_request(
            action_type="RECORD_LAB_RESULT",
            requested_by_agent=requested_by_agent,
            patient_id=patient_id,
            target_type="LAB_ORDER",
            target_id=str(lab_order_id),
            request_payload=payload,
        )

        return self.gateway.execute_action(gateway_request_id)