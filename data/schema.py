"""
Sentinel - Patient Record Schema

Implements the Privacy gate principle: only fields explicitly defined here are processed by the system. Anything else is stripped at validation

Reference: WHO Principle 6 (privacy by design through data minimisation)

"""
from pydantic import BaseModel, Field, ValidationInfo, field_validator, ConfigDict
from typing import Literal, Optional
from datetime import date
from enum import Enum

# --- Enumerations for controlled vocabulary ---


class Ethnicity(str, Enum):
    """Ethnicity categories for fairness auditing.

    These categories are based on standard demographic stratifications
    used in maternal health research. We coarse categories because finer 
    granularity creates statistical instability with small samples

    """
    BLACK_AFRICAN = "black_african"
    WHITE = "white"
    SOUTH_ASIAN = "south_asian"
    EAST_ASIAN = "east_asian"
    OTHER = "other"
    NOT_DISCLOSED = "not_disclosed"


class DiabetesType(str, Enum):
    NONE = "none"
    TYPE_1 = "type_1"
    TYPE_2 = "type_2"
    GESTATIONAL = "gestational"


class SocioeconomicProxy(str, Enum):
    """Coarse socioeconomic indicator for fairness auditing.

    Note: this is a known proxy with documented limitations.
    Real systems should use validated socioeconomic measures.
    """
    LOW = "low"
    MIDDLE = "middle"
    HIGH = "high"
    NOT_DISCLOSED = "not_disclosed"

# --- Sub-schemas for measurements ---


class BloodPressureReading(BaseModel):
    """A single blood pressure measurement at a specific gestational age."""

    gestational_week: int = Field(
        ...,
        description="Gestational week when reading was taken"
    )
    systolic: int = Field(
        ...,
        description="Systolic blood pressure in mmHg"
    )
    diastolic: int = Field(
        ...,
        description="Diastolic blood pressure in mmHg"
    )

    @field_validator("gestational_week")
    @classmethod
    def gestational_week_in_range(cls, value):
        if value < 4 or value > 42:
            raise ValueError(
                f"gestational_week must be between 4 and 42 but got {value}")
        return value

    @field_validator("systolic")
    @classmethod
    def systolic_in_range(cls, value):
        if value < 60 or value > 250:
            raise ValueError(
                f"Systolic blood pressure reading must be between 60 and 250 but got {value}")
        return value

    @field_validator("diastolic")
    @classmethod
    def diastolic_in_range(cls, value):
        if value < 30 or value > 200:
            raise ValueError(
                f"diastolic blood pressure reading must be between 30 and 200 but got {value}")
        return value

    @field_validator("diastolic")
    @classmethod
    def systolic_greater_than_diastolic(cls, value, info: ValidationInfo):
        if "systolic" in info.data and value >= info.data["systolic"]:
            raise ValueError(
                f"systolic ({info.data['systolic']}) must be greater than diastolic ({value})"
            )
        return value


class Symptoms(BaseModel):
    """Patient-reported symptoms at the current visit."""

    headache: bool = False
    visual_disturbance: bool = False
    epigastric_pain: bool = False
    swelling: bool = False

# --- The main patient record schema ---


class PatientRecord(BaseModel):
    """
    Sentinel patient record — minimum-necessary data for pre-eclampsia risk.

    This schema enforces the Privacy Gate principle. Only fields defined
    here are processed by the system. Records with extra fields will have
    those fields stripped during validation.
    """

    model_config = ConfigDict(
        extra="ignore",  # Strip any fields not defined in this schema
        str_strip_whitespace=True,
    )

    # --- Identity (synthetic only, no real PHI) --
    patient_id: str = Field(..., description="Synthetic patient Identifier")
    is_synthetic: bool = Field(
        default=True,
        description="MUST be True. This system processes synthetic data only."
    )

    # --- Identity (synthetic only, no real PHI) ---
    patient_id: str = Field(..., description="Synthetic patient identifier")
    is_synthetic: bool = Field(
        default=True,
        description="MUST be True. This system processes synthetic data only."
    )

    # --- Demographics (required for fairness auditing) ---
    age: int = Field(..., description="Maternal age in years")
    ethnicity: Ethnicity
    socioeconomic_proxy: SocioeconomicProxy

    # --- Pregnancy context ---
    parity: int = Field(...,
                        description="Number of previous pregnancies > 20 weeks")
    multiple_pregnancy: bool = False
    current_gestational_week: int = Field(...,
                                          description="Current gestational week")

    # --- Medical history ---
    pre_existing_hypertension: bool = False
    diabetes: DiabetesType = DiabetesType.NONE
    prior_preeclampsia: bool = False
    family_history_preeclampsia: bool = False
    bmi_at_booking: float = Field(..., description="BMI at booking visit")

    # --- Current pregnancy clinical data ---
    blood_pressure_readings: list[BloodPressureReading] = Field(
        default_factory=list,
        description="All BP readings during current pregnancy"
    )
    proteinuria_level: Optional[float] = Field(
        default=None,
        description="Protein/creatinine ratio (mg/mmol)"
    )
    current_symptoms: Symptoms = Field(default_factory=Symptoms)

    # --- Outcome (for training/eval only — NOT input to predictor) ---
    developed_preeclampsia_by_32w: Optional[bool] = Field(
        default=None,
        description="Outcome label. Only present in training/eval data."
    )

    @field_validator("age")
    @classmethod
    def age_in_range(cls, value):
        if value < 12 or value > 60:
            raise ValueError(
                f"age must be between 12 and 60 (yes, edge cases exist) but got {value}")
        return value

    @field_validator("parity")
    @classmethod
    def parity_non_negative(cls, value):
        if value < 0:
            raise ValueError(f"parity must be 0 or greater but got {value}")
        return value

    @field_validator("current_gestational_week")
    @classmethod
    def gestational_week_valid(cls, value):
        if value < 4 or value > 42:
            raise ValueError(
                f"current_gestational_week must be between 4 and 42 but got {value}")
        return value

    @field_validator("bmi_at_booking")
    @classmethod
    def bmi_in_range(cls, value):
        if value < 12 or value > 70:
            raise ValueError(
                f"bmi_at_booking must be between 12 and 70 but got {value}")
        return value

    @field_validator("is_synthetic")
    @classmethod
    def must_be_synthetic(cls, value):
        if value == False:
            raise ValueError(
            "is_synthetic must be True. System processes synthetic data only."
        )
        return value

    @field_validator("proteinuria_level")
    @classmethod
    def proteinuria_in_range(cls, value):
        if value is None:
            return value

        if value < 0 or value > 1000:
            raise ValueError(
                f"proteinuria_level must be between 0 and 1000 but got {value}")

        return value

# --- Standalone test ---


if __name__ == "__main__":
    # Test 1 — valid record
    valid_record = {
        "patient_id": "SYN-0001",
        "is_synthetic": True,
        "age": 32,
        "ethnicity": "black_african",
        "socioeconomic_proxy": "middle",
        "parity": 1,
        "multiple_pregnancy": False,
        "current_gestational_week": 24,
        "pre_existing_hypertension": False,
        "diabetes": "none",
        "prior_preeclampsia": False,
        "family_history_preeclampsia": True,
        "bmi_at_booking": 28.5,
        "blood_pressure_readings": [
            {"gestational_week": 12, "systolic": 118, "diastolic": 75},
            {"gestational_week": 20, "systolic": 124, "diastolic": 78},
            {"gestational_week": 24, "systolic": 132, "diastolic": 84},
        ],
        "proteinuria_level": 15.0,
        "current_symptoms": {"headache": True, "visual_disturbance": False},
    }

    record = PatientRecord(**valid_record)
    print("Valid record parsed:", record.patient_id)

    # Test 2 — extra field gets stripped
    record_with_extra = {**valid_record, "ssn": "123-45-6789"}
    record = PatientRecord(**record_with_extra)
    assert not hasattr(record, "ssn"), "Extra fields should be stripped"
    print("Extra fields stripped correctly")

    # Test 3 — invalid record (must catch)
    try:
        bad_record = {**valid_record, "is_synthetic": False}
        PatientRecord(**bad_record)
        print("Should have rejected non-synthetic record")
    except Exception as e:
        print(f"Correctly rejected non-synthetic: {type(e).__name__}")

    # Test 4 — invalid age
    try:
        bad_record = {**valid_record, "age": 5}
        PatientRecord(**bad_record)
        print("Should have rejected age 5")
    except Exception as e:
        print(f"Correctly rejected age 5: {type(e).__name__}")

    # Test 5 — invalid BP (systolic < diastolic)
    try:
        bad_record = {
            **valid_record,
            "blood_pressure_readings": [
                {"gestational_week": 12, "systolic": 70, "diastolic": 80}
            ]
        }
        PatientRecord(**bad_record)
        print("Should have rejected systolic < diastolic")
    except Exception as e:
        print(f"Correctly rejected impossible BP: {type(e).__name__}")

    try:
        bad_record = {
            **valid_record,
            "blood_pressure_readings": [
                {"gestational_week": 12, "systolic": 100, "diastolic": 100}
            ]
        }
        PatientRecord(**bad_record)
        print("Should have rejected systolic == diastolic")
    except Exception as e:
        print(f"Correctly rejected systolic == diastolic: {type(e).__name__}")
