import sys
import os
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.receipts.service.image_gen import ReceiptGenerator
from core.receipts.service.receipt_service import ReceiptService
from utilities.dbconfig import SessionLocal, engine
from core.receipts.model.Receipt import Base
import base64
from PIL import Image
import io


def create_test_database():
    """Create test database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")


def test_receipt_generator():
    """Test the receipt generator with updated parameter sets"""
    print("\n🧪 Testing Receipt Generator...")

    generator = ReceiptGenerator()

    # New-format test data
    test_cases = [
        {
            "name": "Basic Transfer",
            "data": {
                'amount': "25.00",
                'transaction_id': "TXN123456789",
                'sender_name': "John Doe",
                'sender_account': "0241234567",
                'sender_provider': "MTN Mobile Money",
                'receiver_name': "Ama Abena",
                'receiver_account': "0559876543",
                'receiver_provider': "Vodafone Cash",
                'status': "Completed",
                'timestamp': datetime.now()
            }
        },
        {
            "name": "Failed Transfer",
            "data": {
                'amount': "80.00",
                'transaction_id': "FAILED_TXN_001",
                'sender_name': "Kwame Mensah",
                'sender_account': "0245001122",
                'sender_provider': "AirtelTigo",
                'receiver_name': "Yaw Boateng",
                'receiver_account': "0594455221",
                'receiver_provider': "MTN Mobile Money",
                'status': "Failed",
                'timestamp': datetime.now()
            }
        },
        {
            "name": "Loan Disbursement",
            "data": {
                'amount': "1000.00",
                'transaction_id': "LN0987654321",
                'sender_name': "Autobus Finance",
                'sender_account': "LBFIN001",
                'sender_provider': "Internal",
                'receiver_name': "Sarah Owusu",
                'receiver_account': "0248889999",
                'receiver_provider': "MTN Mobile Money",
                'status': "Completed",
                'timestamp': datetime.now(),
                'interest_rate': "5",
                'loan_period': "30 days",
                'expected_pay_date': (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                'penalty_rate': "2"
            }
        },
        {
            "name": "Large Loan Disbursement",
            "data": {
                'amount': "5000.00",
                'transaction_id': "LN5000BIG",
                'sender_name': "Autobus Finance",
                'sender_account': "LBFIN001",
                'sender_provider': "Internal",
                'receiver_name': "Michael Asante",
                'receiver_account': "0557766554",
                'receiver_provider': "Vodafone Cash",
                'status': "Completed",
                'timestamp': datetime.now(),
                'interest_rate': "7.5",
                'loan_period': "90 days",
                'expected_pay_date': (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
                'penalty_rate': "3.5"
            }
        },
    ]

    # Create test_output directory
    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)

    for case in test_cases:
        print(f"\n📄 Generating receipt for: {case['name']}")

        try:
            image_url = generator.generate_receipt_image(case["data"])

            print(f"✅ Image URL generated (truncated): {image_url[:50]}...")

            # Decode base64
            base64_data = image_url.split(',')[1]
            image_data = base64.b64decode(base64_data)

            filename = f"{output_dir}/{case['name'].lower().replace(' ', '_')}.png"
            with open(filename, "wb") as f:
                f.write(image_data)

            img = Image.open(io.BytesIO(image_data))
            print(f"   ✔ Saved: {filename}")
            print(f"   ✔ Size: {img.size}")
            print(f"   ✔ Format: {img.format}")

        except Exception as e:
            print(f"❌ Error generating {case['name']}: {e}")


def test_receipt_service():
    """Test the receipt service with updated parameters and DB operations"""
    print("\n\n🧪 Testing Receipt Service with Database...")

    db = SessionLocal()
    try:
        service = ReceiptService(db)

        print("📝 Creating receipt in database...")

        image_url = service.create_receipt(
            user_id="test_user_123",
            amount="75.25",
            transaction_id="TEST_TXN_001",
            sender_name="Test Sender",
            sender_account="0241112222",
            sender_provider="MTN Mobile Money",
            receiver_name="Test Receiver",
            receiver_account="0553334444",
            receiver_provider="Vodafone Cash",
            status="Completed",
            timestamp=datetime.now()
        )

        print("✅ Receipt created!")
        print(f"📸 URL prefix: {image_url[:50]}...")

        # Retrieve by transaction ID
        retrieved = service.get_receipt_image_url_by_transaction("TEST_TXN_001")
        print(f"🔎 Retrieved receipt URL length: {len(retrieved)}")

        # Get recent receipts
        receipts = service.get_user_receipts("test_user_123", limit=5)
        print(f"👤 {len(receipts)} receipts found.")

        # Save a file
        base64_data = image_url.split(',')[1]
        image_data = base64.b64decode(base64_data)
        filename = "test_output/service_generated_receipt.png"
        with open(filename, "wb") as f:
            f.write(image_data)

        print(f"💾 Saved service output: {filename}")

    except Exception as e:
        print(f"❌ Error in receipt service test: {e}")

    finally:
        db.close()


def test_edge_cases():
    """Test edge cases using new parameter format"""
    print("\n\n⚠️ Testing Edge Cases...")

    generator = ReceiptGenerator()

    edge_cases = [
        {
            "name": "Missing Fields",
            "data": {
                'amount': "10.00",
                'transaction_id': "TXNMISSING01",
                'status': "Completed"
                # Missing sender/receiver details
            }
        },
        {
            "name": "Long Transaction ID",
            "data": {
                'amount': "10.00",
                'transaction_id': "THIS_IS_A_SUPER_LONG_TRANSACTION_ID_THAT_SHOULD_WRAP_PROPERLY_IN_THE_RECEIPT",
                'sender_name': "Test",
                'sender_account': "00000000",
                'sender_provider': "MTN",
                'receiver_name': "Receiver",
                'receiver_account': "11111111",
                'receiver_provider': "Vodafone",
                'status': "Completed",
                'timestamp': datetime.now()
            }
        },
        {
            "name": "Zero Amount",
            "data": {
                'amount': "0.00",
                'transaction_id': "ZERO_TXN_01",
                'sender_name': "Test Sender",
                'sender_account': "0241112222",
                'sender_provider': "AirtelTigo",
                'receiver_name': "Test Receiver",
                'receiver_account': "0509997777",
                'receiver_provider': "Vodafone",
                'status': "Completed",
                'timestamp': datetime.now()
            }
        },
        {
            "name": "Failed Transaction",
            "data": {
                'amount': "50.00",
                'transaction_id': "FAILED_TEST_01",
                'sender_name': "Test Sender",
                'sender_account': "0241112222",
                'sender_provider': "AirtelTigo",
                'receiver_name': "Test Receiver",
                'receiver_account': "0509997777",
                'receiver_provider': "Vodafone",
                'status': "Failed",
                'timestamp': datetime.now()
            }
        }
    ]

    for case in edge_cases:
        print(f"\n🔧 Testing: {case['name']}")

        try:
            image_url = generator.generate_receipt_image(case["data"])

            base64_data = image_url.split(',')[1]
            image_data = base64.b64decode(base64_data)

            filename = f"test_output/edge_{case['name'].lower().replace(' ', '_')}.png"
            with open(filename, "wb") as f:
                f.write(image_data)

            print(f"✔ Saved: {filename}")

        except Exception as e:
            print(f"❌ Error in edge case '{case['name']}': {e}")


def main():
    """Run all tests"""
    print("🚀 Starting Receipt Generation Tests")
    print("=" * 50)

    os.makedirs("test_output", exist_ok=True)

    try:
        create_test_database()
        test_receipt_generator()
        test_receipt_service()
        test_edge_cases()

        print("\n🎉 All tests completed!")
        print("📁 Check 'test_output/' for generated images.")

    except Exception as e:
        print(f"💥 Critical Error: {e}")


if __name__ == "__main__":
    main()
