"""
Fee Management REST API routes.
"""

from datetime import datetime, date
import uuid
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models.fees import FeeRecord, FeePayment
from security.decorators import admin_required

fees_bp = Blueprint("fees_bp", __name__, url_prefix="/fees")


@fees_bp.route("/student/<int:student_id>", methods=["GET"])
@login_required
def student_fees(student_id: int):
    if current_user.role.name == "student" and (not current_user.student_profile or current_user.student_profile.id != student_id):
        return jsonify({"success": False, "message": "Access denied."}), 403

    records = FeeRecord.query.filter_by(student_id=student_id).all()
    return jsonify({
        "success": True,
        "fee_records": [r.to_dict() for r in records],
    })


@fees_bp.route("/record", methods=["POST"])
@login_required
@admin_required
def create_fee_record():
    data = request.get_json() or {}
    student_id = data.get("student_id")
    semester_id = data.get("semester_id")
    academic_year_id = data.get("academic_year_id")
    fee_type = data.get("fee_type", "tuition")
    total_amount = data.get("total_amount")
    due_date_str = data.get("due_date")

    if not all([student_id, semester_id, academic_year_id, total_amount, due_date_str]):
        return jsonify({"success": False, "message": "Missing required fields."}), 400

    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()

    record = FeeRecord(
        student_id=student_id,
        semester_id=semester_id,
        academic_year_id=academic_year_id,
        fee_type=fee_type,
        description=data.get("description"),
        total_amount=total_amount,
        due_date=due_date,
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({"success": True, "fee_record": record.to_dict()})


@fees_bp.route("/payment", methods=["POST"])
@login_required
@admin_required
def record_payment():
    data = request.get_json() or {}
    fee_record_id = data.get("fee_record_id")
    amount = float(data.get("amount", 0.0))
    payment_mode = data.get("payment_mode", "cash")
    receipt_no = data.get("receipt_number") or f"REC-{uuid.uuid4().hex[:8].upper()}"

    record = FeeRecord.query.get_or_404(fee_record_id)
    payment = FeePayment(
        fee_record_id=record.id,
        amount_paid=amount,
        payment_mode=payment_mode,
        transaction_reference=data.get("transaction_reference"),
        receipt_number=receipt_no,
        remarks=data.get("remarks"),
        received_by_user_id=current_user.id,
    )

    record.amount_paid = float(record.amount_paid or 0.0) + amount
    record.update_payment_status()

    db.session.add(payment)
    db.session.commit()

    return jsonify({
        "success": True,
        "payment": payment.to_dict(),
        "new_balance": record.balance_amount,
        "payment_status": record.payment_status,
    })


@fees_bp.route("/summary", methods=["GET"])
@login_required
@admin_required
def fee_summary():
    records = FeeRecord.query.all()
    total_assigned = sum(float(r.total_amount or 0) for r in records)
    total_collected = sum(float(r.amount_paid or 0) for r in records)
    total_pending = max(0.0, total_assigned - total_collected)

    return jsonify({
        "success": True,
        "total_assigned": total_assigned,
        "total_collected": total_collected,
        "total_pending": total_pending,
    })
