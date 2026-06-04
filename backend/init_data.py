from app import app, db, ComputerAsset, DeviceAsset, User
from datetime import datetime, date

def init_sample_data():
    with app.app_context():
        # Clear asset tables only (preserve user accounts)
        ComputerAsset.query.delete()
        DeviceAsset.query.delete()
        db.session.commit()
        
        # Ensure admin account exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                department='IT',
                position='System Administrator',
                is_admin=True
            )
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            print("Admin account created: admin/admin")
        
        print("All asset data cleared!")
        print("Admin account preserved: admin/admin")

if __name__ == '__main__':
    init_sample_data()