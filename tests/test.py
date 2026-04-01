import sys
sys.path.insert(0, "src")

from dotenv import load_dotenv
load_dotenv()

from misconception_detector import detect_misconceptions

result = detect_misconceptions(
    student_name="Frank",
    explanation="I think fractions are just two numbers with a line between them. I picked the answer that looked right.",
    weak_concepts=["Fractions", "Algebra"]
)

print("\nMisconception Analysis")
print("=" * 50)
print(result)