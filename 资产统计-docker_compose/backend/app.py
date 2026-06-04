from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import os
import shutil
import glob

# 前端目录路径
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')
# 备份目录路径（支持环境变量覆盖，用于Docker部署）
backup_dir = os.environ.get('BACKUP_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backup'))

app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
CORS(app, supports_credentials=True)

# 配置
basedir = os.path.abspath(os.path.dirname(__file__))
# 数据库路径（支持环境变量覆盖，用于Docker部署）
data_dir = os.environ.get('DATA_DIR', basedir)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(data_dir, 'assets.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'asset-management-secret-key-2026'

# 确保备份目录存在
os.makedirs(backup_dir, exist_ok=True)

# 前端页面路由
@app.route('/')
def serve_frontend():
    return send_from_directory(frontend_dir, 'index.html')

db = SQLAlchemy(app)

# 认证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# 权限检查装饰器
def permission_required(asset_type, permission_type='view'):
    """
    权限检查装饰器
    asset_type: 'computer' 或 'device'
    permission_type: 'view' (查看) 或 'edit' (编辑)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Authentication required'}), 401
            
            user = User.query.get(session['user_id'])
            if not user:
                return jsonify({'error': 'User not found'}), 401
            
            # 管理员拥有所有权限
            if user.is_admin:
                return f(*args, **kwargs)
            
            import json
            permissions = json.loads(user.permissions) if user.permissions else {}
            asset_permission = permissions.get(asset_type, 'none')
            
            # 检查权限
            if permission_type == 'view':
                if asset_permission == 'none':
                    return jsonify({'error': '没有查看权限'}), 403
            elif permission_type == 'edit':
                if asset_permission != 'edit':
                    return jsonify({'error': '没有编辑权限'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 电脑资产模型
class ComputerAsset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_no = db.Column(db.String(50), unique=True, nullable=False)  # 资产编号（必填）
    asset_model = db.Column(db.String(100))  # 资产型号
    serial_number = db.Column(db.String(100))  # 序列号
    mac_address = db.Column(db.String(50))  # MAC地址
    ip_address = db.Column(db.String(50))  # IP地址
    user_name = db.Column(db.String(50))  # 使用人
    department = db.Column(db.String(100))  # 使用部门
    receive_date = db.Column(db.Date)  # 领用日期
    status = db.Column(db.String(20), default='in_use')  # 状态：in_use/stock/fault
    supplier = db.Column(db.String(200))  # 供应商
    entry_amount = db.Column(db.Float)  # 入账金额
    entry_date = db.Column(db.Date)  # 入账日期
    remark = db.Column(db.Text)  # 备注
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'asset_no': self.asset_no,
            'asset_model': self.asset_model,
            'serial_number': self.serial_number,
            'mac_address': self.mac_address,
            'ip_address': self.ip_address,
            'user_name': self.user_name,
            'department': self.department,
            'receive_date': self.receive_date.isoformat() if self.receive_date else None,
            'status': self.status,
            'supplier': self.supplier,
            'entry_amount': self.entry_amount,
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'remark': self.remark,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# 设备资产模型
class DeviceAsset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_no = db.Column(db.String(50), unique=True, nullable=False)  # 资产编号（必填）
    asset_model = db.Column(db.String(100))  # 资产型号
    serial_number = db.Column(db.String(100))  # 序列号
    user_name = db.Column(db.String(50))  # 使用人
    department = db.Column(db.String(100))  # 使用部门
    location = db.Column(db.String(100))  # 使用位置
    status = db.Column(db.String(20), default='in_use')  # 状态：in_use/stock/normal/fault
    supplier = db.Column(db.String(200))  # 供应商
    entry_amount = db.Column(db.Float)  # 入账金额
    entry_date = db.Column(db.Date)  # 入账日期
    remark = db.Column(db.Text)  # 备注
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'asset_no': self.asset_no,
            'asset_model': self.asset_model,
            'serial_number': self.serial_number,
            'user_name': self.user_name,
            'department': self.department,
            'location': self.location,
            'status': self.status,
            'supplier': self.supplier,
            'entry_amount': self.entry_amount,
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'remark': self.remark,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# 用户模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    department = db.Column(db.String(100))
    position = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    # 权限字段：JSON格式存储各模块权限 {module: {view: bool, edit: bool}}
    permissions = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'department': self.department,
            'position': self.position,
            'is_admin': self.is_admin,
            'permissions': json.loads(self.permissions) if self.permissions else {},
            'created_at': self.created_at.isoformat()
        }

# 资产入账设置模型
class AssetFieldConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_type = db.Column(db.String(20), nullable=False)  # computer / device
    field_name = db.Column(db.String(50), nullable=False)  # 字段名
    field_label = db.Column(db.String(50), nullable=False)  # 字段显示名
    visible = db.Column(db.Boolean, default=True)  # 是否显示
    required = db.Column(db.Boolean, default=False)  # 是否必填
    order = db.Column(db.Integer, default=0)  # 排序

    def to_dict(self):
        return {
            'id': self.id,
            'asset_type': self.asset_type,
            'field_name': self.field_name,
            'field_label': self.field_label,
            'visible': self.visible,
            'required': self.required,
            'order': self.order
        }

# 调拨记录模型
class TransferRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_type = db.Column(db.String(20), nullable=False)  # computer / device
    asset_no = db.Column(db.String(50), nullable=False)  # 资产编号
    transfer_type = db.Column(db.String(20), nullable=False)  # to_stock / to_user
    target_user = db.Column(db.String(50))  # 目标用户（调给人时）
    target_department = db.Column(db.String(100))  # 目标部门
    target_location = db.Column(db.String(100))  # 目标位置
    remark = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        asset_type_name = '电脑资产' if self.asset_type == 'computer' else '设备资产'
        transfer_type_name = '退库' if self.transfer_type == 'to_stock' else '调拨'
        return {
            'id': self.id,
            'asset_type': self.asset_type,
            'asset_type_name': asset_type_name,
            'asset_no': self.asset_no,
            'transfer_type': self.transfer_type,
            'transfer_type_name': transfer_type_name,
            'target_user': self.target_user,
            'target_department': self.target_department,
            'target_location': self.target_location,
            'remark': self.remark,
            'created_at': self.created_at.isoformat()
        }

# 创建数据库表
with app.app_context():
    db.create_all()
    # 数据库迁移
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        
        # 检查并创建asset_field_config表
        existing_tables = inspector.get_table_names()
        if 'asset_field_config' not in existing_tables:
            AssetFieldConfig.__table__.create(db.engine)
            print("Created asset_field_config table")
        
        # 迁移user表添加permissions字段
        if 'user' in existing_tables:
            user_columns = [col['name'] for col in inspector.get_columns('user')]
            if 'permissions' not in user_columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE "user" ADD COLUMN permissions TEXT DEFAULT "{}"'))
                    conn.commit()
                print("Added permissions column to user table")
        
        # 迁移device_asset表
        if 'device_asset' in existing_tables:
            device_columns = [col['name'] for col in inspector.get_columns('device_asset')]
            if 'status' not in device_columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE device_asset ADD COLUMN status VARCHAR(20) DEFAULT "in_use"'))
                    conn.commit()
                print("Added status column to device_asset table")
            if 'serial_number' not in device_columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE device_asset ADD COLUMN serial_number VARCHAR(100)'))
                    conn.commit()
                print("Added serial_number column to device_asset table")
            if 'supplier' not in device_columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE device_asset ADD COLUMN supplier VARCHAR(200)'))
                    conn.commit()
                print("Added supplier column to device_asset table")
            if 'entry_amount' not in device_columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE device_asset ADD COLUMN entry_amount FLOAT'))
                    conn.commit()
                print("Added entry_amount column to device_asset table")
            if 'entry_date' not in device_columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE device_asset ADD COLUMN entry_date DATE'))
                    conn.commit()
                print("Added entry_date column to device_asset table")
        
        # 迁移computer_asset表
        if 'computer_asset' in existing_tables:
            computer_columns = [col['name'] for col in inspector.get_columns('computer_asset')]
            if 'serial_number' not in computer_columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE computer_asset ADD COLUMN serial_number VARCHAR(100)'))
                    conn.commit()
                print("Added serial_number column to computer_asset table")
            if 'supplier' not in computer_columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE computer_asset ADD COLUMN supplier VARCHAR(200)'))
                    conn.commit()
                print("Added supplier column to computer_asset table")
            if 'entry_amount' not in computer_columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE computer_asset ADD COLUMN entry_amount FLOAT'))
                    conn.commit()
                print("Added entry_amount column to computer_asset table")
            if 'entry_date' not in computer_columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE computer_asset ADD COLUMN entry_date DATE'))
                    conn.commit()
                print("Added entry_date column to computer_asset table")
            
    except Exception as e:
        print(f"Migration check: {e}")
    
    # 创建默认管理员账号（如果不存在）
    try:
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
            print("Default admin account created: admin/admin")
    except Exception as e:
        print(f"Admin creation check: {e}")
    
    # 初始化资产入账字段配置（如果不存在）
    try:
        if AssetFieldConfig.query.count() == 0:
            default_fields = [
                {'asset_type': 'computer', 'field_name': 'asset_no', 'field_label': '资产编号', 'visible': True, 'required': True, 'order': 1},
                {'asset_type': 'computer', 'field_name': 'asset_model', 'field_label': '资产型号', 'visible': True, 'required': False, 'order': 2},
                {'asset_type': 'computer', 'field_name': 'serial_number', 'field_label': '序列号', 'visible': True, 'required': False, 'order': 3},
                {'asset_type': 'computer', 'field_name': 'mac_address', 'field_label': 'MAC地址', 'visible': True, 'required': False, 'order': 4},
                {'asset_type': 'computer', 'field_name': 'ip_address', 'field_label': 'IP地址', 'visible': True, 'required': False, 'order': 5},
                {'asset_type': 'computer', 'field_name': 'user_name', 'field_label': '使用人', 'visible': True, 'required': False, 'order': 6},
                {'asset_type': 'computer', 'field_name': 'department', 'field_label': '使用部门', 'visible': True, 'required': False, 'order': 7},
                {'asset_type': 'computer', 'field_name': 'receive_date', 'field_label': '领用日期', 'visible': True, 'required': False, 'order': 8},
                {'asset_type': 'computer', 'field_name': 'supplier', 'field_label': '供应商', 'visible': True, 'required': False, 'order': 9},
                {'asset_type': 'computer', 'field_name': 'entry_amount', 'field_label': '入账金额', 'visible': True, 'required': False, 'order': 10},
                {'asset_type': 'computer', 'field_name': 'entry_date', 'field_label': '入账日期', 'visible': True, 'required': False, 'order': 11},
                {'asset_type': 'computer', 'field_name': 'remark', 'field_label': '备注', 'visible': True, 'required': False, 'order': 12},
                {'asset_type': 'device', 'field_name': 'asset_no', 'field_label': '资产编号', 'visible': True, 'required': True, 'order': 1},
                {'asset_type': 'device', 'field_name': 'asset_model', 'field_label': '资产型号', 'visible': True, 'required': False, 'order': 2},
                {'asset_type': 'device', 'field_name': 'serial_number', 'field_label': '序列号', 'visible': True, 'required': False, 'order': 3},
                {'asset_type': 'device', 'field_name': 'user_name', 'field_label': '使用人', 'visible': True, 'required': False, 'order': 4},
                {'asset_type': 'device', 'field_name': 'department', 'field_label': '使用部门', 'visible': True, 'required': False, 'order': 5},
                {'asset_type': 'device', 'field_name': 'location', 'field_label': '使用位置', 'visible': True, 'required': False, 'order': 6},
                {'asset_type': 'device', 'field_name': 'supplier', 'field_label': '供应商', 'visible': True, 'required': False, 'order': 7},
                {'asset_type': 'device', 'field_name': 'entry_amount', 'field_label': '入账金额', 'visible': True, 'required': False, 'order': 8},
                {'asset_type': 'device', 'field_name': 'entry_date', 'field_label': '入账日期', 'visible': True, 'required': False, 'order': 9},
                {'asset_type': 'device', 'field_name': 'remark', 'field_label': '备注', 'visible': True, 'required': False, 'order': 10},
            ]
            for field in default_fields:
                db.session.add(AssetFieldConfig(**field))
            db.session.commit()
            print("Default asset field configurations created")
    except Exception as e:
        print(f"Field config init error: {e}")

# 认证API
@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': '用户名和密码不能为空'}), 400
        
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            return jsonify({'error': '用户名或密码错误'}), 401
        
        session['user_id'] = user.id
        session['username'] = user.username
        session['is_admin'] = user.is_admin
        
        return jsonify({
            'message': '登录成功',
            'user': user.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': '退出登录成功'})

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return jsonify({
                'authenticated': True,
                'user': user.to_dict()
            })
    return jsonify({'authenticated': False}), 401

@app.route('/api/auth/permissions', methods=['GET'])
@login_required
def get_permissions():
    """获取当前用户的权限信息"""
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        import json
        permissions = json.loads(user.permissions) if user.permissions else {}
        
        # 管理员拥有所有权限
        if user.is_admin:
            return jsonify({
                'is_admin': True,
                'permissions': {
                    'computer': 'edit',
                    'device': 'edit'
                }
            })
        
        return jsonify({
            'is_admin': False,
            'permissions': permissions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 首页统计API（需要认证）
@app.route('/api/dashboard')
@login_required
def dashboard():
    try:
        # 检查用户权限
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 401

        import json
        permissions = json.loads(user.permissions) if user.permissions else {}
        computer_perm = permissions.get('computer', 'none') if not user.is_admin else 'edit'
        device_perm = permissions.get('device', 'none') if not user.is_admin else 'edit'

        computer_count = ComputerAsset.query.count() if computer_perm != 'none' else 0
        device_count = DeviceAsset.query.count() if device_perm != 'none' else 0
        user_count = User.query.count() if user.is_admin else 0

        # 按状态统计电脑
        computer_status = {}
        if computer_perm != 'none':
            computer_status_list = db.session.query(
                ComputerAsset.status,
                db.func.count(ComputerAsset.id)
            ).group_by(ComputerAsset.status).all()
            computer_status = dict(computer_status_list)

        # 按状态统计设备
        device_status = {}
        if device_perm != 'none':
            device_status_list = db.session.query(
                DeviceAsset.status,
                db.func.count(DeviceAsset.id)
            ).group_by(DeviceAsset.status).all()
            device_status = dict(device_status_list)

        return jsonify({
            'computer_count': computer_count,
            'device_count': device_count,
            'user_count': user_count,
            'computer_status': computer_status,
            'device_status': device_status
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 综合搜索API（需要认证）
@app.route('/api/search', methods=['GET'])
@login_required
def search_assets():
    try:
        # 检查用户权限
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 401

        import json
        permissions = json.loads(user.permissions) if user.permissions else {}
        computer_perm = permissions.get('computer', 'none') if not user.is_admin else 'edit'
        device_perm = permissions.get('device', 'none') if not user.is_admin else 'edit'

        if computer_perm == 'none' and device_perm == 'none':
            return jsonify({'error': '没有查看权限'}), 403

        keyword = request.args.get('keyword', '').strip()
        if not keyword:
            return jsonify({'computers': [], 'devices': []})

        computers = []
        if computer_perm != 'none':
            computers = ComputerAsset.query.filter(
                ComputerAsset.user_name.like(f'%{keyword}%')
            ).all()

        devices = []
        if device_perm != 'none':
            devices = DeviceAsset.query.filter(
                DeviceAsset.user_name.like(f'%{keyword}%')
            ).all()

        return jsonify({
            'computers': [c.to_dict() for c in computers],
            'devices': [d.to_dict() for d in devices]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 电脑资产API（需要认证和权限）
@app.route('/api/computers', methods=['GET'])
@login_required
@permission_required('computer', 'view')
def get_computers():
    try:
        computers = ComputerAsset.query.all()
        return jsonify([c.to_dict() for c in computers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/computers', methods=['POST'])
@login_required
@permission_required('computer', 'edit')
def create_computer():
    try:
        data = request.json
        if not data.get('asset_no'):
            return jsonify({'error': '资产编号不能为空'}), 400
        computer = ComputerAsset(
            asset_no=data['asset_no'],
            asset_model=data.get('asset_model'),
            serial_number=data.get('serial_number'),
            mac_address=data.get('mac_address'),
            ip_address=data.get('ip_address'),
            user_name=data.get('user_name'),
            department=data.get('department'),
            receive_date=datetime.strptime(data['receive_date'], '%Y-%m-%d').date() if data.get('receive_date') else None,
            status=data.get('status', 'active'),
            supplier=data.get('supplier'),
            entry_amount=float(data['entry_amount']) if data.get('entry_amount') else None,
            entry_date=datetime.strptime(data['entry_date'], '%Y-%m-%d').date() if data.get('entry_date') else None,
            remark=data.get('remark')
        )
        db.session.add(computer)
        db.session.commit()
        return jsonify(computer.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/computers/<int:id>', methods=['PUT'])
@login_required
@permission_required('computer', 'edit')
def update_computer(id):
    try:
        computer = ComputerAsset.query.get_or_404(id)
        data = request.json
        
        if 'asset_no' in data:
            computer.asset_no = data['asset_no']
        if 'asset_model' in data:
            computer.asset_model = data['asset_model']
        if 'serial_number' in data:
            computer.serial_number = data['serial_number']
        if 'mac_address' in data:
            computer.mac_address = data['mac_address']
        if 'ip_address' in data:
            computer.ip_address = data['ip_address']
        if 'user_name' in data:
            computer.user_name = data['user_name']
        if 'department' in data:
            computer.department = data['department']
        if 'receive_date' in data:
            computer.receive_date = datetime.strptime(data['receive_date'], '%Y-%m-%d').date() if data['receive_date'] else None
        if 'status' in data:
            computer.status = data['status']
        if 'supplier' in data:
            computer.supplier = data['supplier']
        if 'entry_amount' in data:
            computer.entry_amount = float(data['entry_amount']) if data['entry_amount'] else None
        if 'entry_date' in data:
            computer.entry_date = datetime.strptime(data['entry_date'], '%Y-%m-%d').date() if data['entry_date'] else None
        if 'remark' in data:
            computer.remark = data['remark']
        
        db.session.commit()
        return jsonify(computer.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/computers/<int:id>', methods=['DELETE'])
@login_required
@permission_required('computer', 'edit')
def delete_computer(id):
    try:
        computer = ComputerAsset.query.get_or_404(id)
        db.session.delete(computer)
        db.session.commit()
        return jsonify({'message': '电脑资产已删除'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 设备资产API（需要认证和权限）
@app.route('/api/devices', methods=['GET'])
@login_required
@permission_required('device', 'view')
def get_devices():
    try:
        devices = DeviceAsset.query.all()
        return jsonify([d.to_dict() for d in devices])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/devices', methods=['POST'])
@login_required
@permission_required('device', 'edit')
def create_device():
    try:
        data = request.json
        if not data.get('asset_no'):
            return jsonify({'error': '资产编号不能为空'}), 400
        device = DeviceAsset(
            asset_no=data['asset_no'],
            asset_model=data.get('asset_model'),
            serial_number=data.get('serial_number'),
            user_name=data.get('user_name'),
            department=data.get('department'),
            location=data.get('location'),
            supplier=data.get('supplier'),
            entry_amount=float(data['entry_amount']) if data.get('entry_amount') else None,
            entry_date=datetime.strptime(data['entry_date'], '%Y-%m-%d').date() if data.get('entry_date') else None,
            remark=data.get('remark')
        )
        db.session.add(device)
        db.session.commit()
        return jsonify(device.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/devices/<int:id>', methods=['PUT'])
@login_required
@permission_required('device', 'edit')
def update_device(id):
    try:
        device = DeviceAsset.query.get_or_404(id)
        data = request.json
        
        if 'asset_no' in data:
            device.asset_no = data['asset_no']
        if 'asset_model' in data:
            device.asset_model = data['asset_model']
        if 'serial_number' in data:
            device.serial_number = data['serial_number']
        if 'user_name' in data:
            device.user_name = data['user_name']
        if 'department' in data:
            device.department = data['department']
        if 'location' in data:
            device.location = data['location']
        if 'supplier' in data:
            device.supplier = data['supplier']
        if 'entry_amount' in data:
            device.entry_amount = float(data['entry_amount']) if data['entry_amount'] else None
        if 'entry_date' in data:
            device.entry_date = datetime.strptime(data['entry_date'], '%Y-%m-%d').date() if data['entry_date'] else None
        if 'remark' in data:
            device.remark = data['remark']
        
        db.session.commit()
        return jsonify(device.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/devices/<int:id>', methods=['DELETE'])
@login_required
@permission_required('device', 'edit')
def delete_device(id):
    try:
        device = DeviceAsset.query.get_or_404(id)
        db.session.delete(device)
        db.session.commit()
        return jsonify({'message': '设备资产已删除'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 导出电脑资产为xlsx
@app.route('/api/computers/export', methods=['GET'])
@login_required
@permission_required('computer', 'view')
def export_computers():
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from io import BytesIO

        computers = ComputerAsset.query.all()

        wb = Workbook()
        ws = wb.active
        ws.title = "电脑资产台账"

        # 定义样式
        header_font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='CF0A2C', end_color='CF0A2C', fill_type='solid')
        header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        title_font = Font(name='微软雅黑', size=16, bold=True, color='CF0A2C')
        title_alignment = Alignment(horizontal='center', vertical='center')

        data_font = Font(name='微软雅黑', size=10)
        data_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        data_alignment_left = Alignment(horizontal='left', vertical='center', wrap_text=True)

        # 边框样式
        thin_border = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )

        # 交替行颜色
        even_fill = PatternFill(start_color='F5F7FA', end_color='F5F7FA', fill_type='solid')

        # 标题行
        ws.merge_cells('A1:L1')
        title_cell = ws['A1']
        title_cell.value = '电脑资产台账'
        title_cell.font = title_font
        title_cell.alignment = title_alignment
        ws.row_dimensions[1].height = 40

        # 统计信息行
        ws.merge_cells('A2:L2')
        stats_cell = ws['A2']
        stats_cell.value = f'导出时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}    共 {len(computers)} 条记录'
        stats_cell.font = Font(name='微软雅黑', size=9, color='666666')
        stats_cell.alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[2].height = 25

        # 表头
        headers = [
            ('A', '资产编号', 15),
            ('B', '资产型号', 18),
            ('C', '序列号', 18),
            ('D', 'MAC地址', 18),
            ('E', 'IP地址', 15),
            ('F', '使用人', 10),
            ('G', '使用部门', 12),
            ('H', '领用日期', 12),
            ('I', '状态', 8),
            ('J', '供应商', 20),
            ('K', '入账金额', 12),
            ('L', '入账日期', 12),
        ]

        row = 3
        for col_letter, header_name, width in headers:
            cell = ws[f'{col_letter}{row}']
            cell.value = header_name
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
            ws.column_dimensions[col_letter].width = width

        ws.row_dimensions[row].height = 30

        # 状态映射
        status_map = {
            'in_use': '在用',
            'stock': '库存',
            'fault': '故障',
            'active': '在用'
        }

        # 数据行
        for idx, computer in enumerate(computers):
            row = idx + 4
            ws.row_dimensions[row].height = 28

            row_data = [
                computer.asset_no,
                computer.asset_model or '-',
                computer.serial_number or '-',
                computer.mac_address or '-',
                computer.ip_address or '-',
                computer.user_name or '-',
                computer.department or '-',
                computer.receive_date.strftime('%Y-%m-%d') if computer.receive_date else '-',
                status_map.get(computer.status, computer.status),
                computer.supplier or '-',
                computer.entry_amount if computer.entry_amount else '-',
                computer.entry_date.strftime('%Y-%m-%d') if computer.entry_date else '-'
            ]

            for col_idx, value in enumerate(row_data):
                col_letter = chr(65 + col_idx)
                cell = ws[f'{col_letter}{row}']
                cell.value = value
                cell.font = data_font
                cell.border = thin_border

                # 金额列右对齐
                if col_idx == 10 and isinstance(value, (int, float)):
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                    cell.number_format = '#,##0.00'
                # 资产编号、使用人等左对齐
                elif col_idx in [0, 5, 9]:
                    cell.alignment = data_alignment_left
                else:
                    cell.alignment = data_alignment

                # 交替行颜色
                if idx % 2 == 1:
                    cell.fill = even_fill

        # 冻结表头
        ws.freeze_panes = 'A4'

        # 自动筛选
        ws.auto_filter.ref = f'A3:L{len(computers) + 3}'

        # 保存到内存
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        from flask import send_file
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'电脑资产台账_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 导出设备资产为xlsx
@app.route('/api/devices/export', methods=['GET'])
@login_required
@permission_required('device', 'view')
def export_devices():
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from io import BytesIO

        devices = DeviceAsset.query.all()

        wb = Workbook()
        ws = wb.active
        ws.title = "设备资产台账"

        # 定义样式
        header_font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='CF0A2C', end_color='CF0A2C', fill_type='solid')
        header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        title_font = Font(name='微软雅黑', size=16, bold=True, color='CF0A2C')
        title_alignment = Alignment(horizontal='center', vertical='center')

        data_font = Font(name='微软雅黑', size=10)
        data_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        data_alignment_left = Alignment(horizontal='left', vertical='center', wrap_text=True)

        # 边框样式
        thin_border = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )

        # 交替行颜色
        even_fill = PatternFill(start_color='F5F7FA', end_color='F5F7FA', fill_type='solid')

        # 标题行
        ws.merge_cells('A1:J1')
        title_cell = ws['A1']
        title_cell.value = '设备资产台账'
        title_cell.font = title_font
        title_cell.alignment = title_alignment
        ws.row_dimensions[1].height = 40

        # 统计信息行
        ws.merge_cells('A2:J2')
        stats_cell = ws['A2']
        stats_cell.value = f'导出时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}    共 {len(devices)} 条记录'
        stats_cell.font = Font(name='微软雅黑', size=9, color='666666')
        stats_cell.alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[2].height = 25

        # 表头
        headers = [
            ('A', '资产编号', 15),
            ('B', '资产型号', 18),
            ('C', '序列号', 18),
            ('D', '使用人', 10),
            ('E', '使用部门', 12),
            ('F', '使用位置', 15),
            ('G', '状态', 8),
            ('H', '供应商', 20),
            ('I', '入账金额', 12),
            ('J', '入账日期', 12),
        ]

        row = 3
        for col_letter, header_name, width in headers:
            cell = ws[f'{col_letter}{row}']
            cell.value = header_name
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
            ws.column_dimensions[col_letter].width = width

        ws.row_dimensions[row].height = 30

        # 状态映射
        status_map = {
            'in_use': '在用',
            'stock': '库存',
            'fault': '故障',
            'normal': '正常'
        }

        # 数据行
        for idx, device in enumerate(devices):
            row = idx + 4
            ws.row_dimensions[row].height = 28

            row_data = [
                device.asset_no,
                device.asset_model or '-',
                device.serial_number or '-',
                device.user_name or '-',
                device.department or '-',
                device.location or '-',
                status_map.get(device.status, device.status),
                device.supplier or '-',
                device.entry_amount if device.entry_amount else '-',
                device.entry_date.strftime('%Y-%m-%d') if device.entry_date else '-'
            ]

            for col_idx, value in enumerate(row_data):
                col_letter = chr(65 + col_idx)
                cell = ws[f'{col_letter}{row}']
                cell.value = value
                cell.font = data_font
                cell.border = thin_border

                # 金额列右对齐
                if col_idx == 8 and isinstance(value, (int, float)):
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                    cell.number_format = '#,##0.00'
                # 资产编号、使用人等左对齐
                elif col_idx in [0, 3, 7]:
                    cell.alignment = data_alignment_left
                else:
                    cell.alignment = data_alignment

                # 交替行颜色
                if idx % 2 == 1:
                    cell.fill = even_fill

        # 冻结表头
        ws.freeze_panes = 'A4'

        # 自动筛选
        ws.auto_filter.ref = f'A3:J{len(devices) + 3}'

        # 保存到内存
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        from flask import send_file
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'设备资产台账_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 下载电脑资产导入模板
@app.route('/api/computers/template', methods=['GET'])
@login_required
@permission_required('computer', 'edit')
def download_computer_template():
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from io import BytesIO

        wb = Workbook()
        ws = wb.active
        ws.title = "电脑资产导入模板"

        # 定义样式
        header_font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='CF0A2C', end_color='CF0A2C', fill_type='solid')
        header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        title_font = Font(name='微软雅黑', size=16, bold=True, color='CF0A2C')
        title_alignment = Alignment(horizontal='center', vertical='center')

        note_font = Font(name='微软雅黑', size=9, color='FF0000')
        note_alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

        example_font = Font(name='微软雅黑', size=10, color='999999')
        example_alignment = Alignment(horizontal='center', vertical='center')

        # 边框样式
        thin_border = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )

        # 标题行
        ws.merge_cells('A1:L1')
        title_cell = ws['A1']
        title_cell.value = '电脑资产导入模板'
        title_cell.font = title_font
        title_cell.alignment = title_alignment
        ws.row_dimensions[1].height = 40

        # 说明行
        ws.merge_cells('A2:L2')
        note_cell = ws['A2']
        note_cell.value = '说明：带 * 号的字段为必填项；状态可选值：在用、库存、故障；日期格式：YYYY-MM-DD（如：2026-01-15）'
        note_cell.font = note_font
        note_cell.alignment = note_alignment
        ws.row_dimensions[2].height = 30

        # 表头
        headers = [
            ('A', '资产编号 *', 15),
            ('B', '资产型号', 18),
            ('C', '序列号', 18),
            ('D', 'MAC地址', 18),
            ('E', 'IP地址', 15),
            ('F', '使用人', 10),
            ('G', '使用部门', 12),
            ('H', '领用日期', 12),
            ('I', '状态', 8),
            ('J', '供应商', 20),
            ('K', '入账金额', 12),
            ('L', '入账日期', 12),
        ]

        row = 3
        for col_letter, header_name, width in headers:
            cell = ws[f'{col_letter}{row}']
            cell.value = header_name
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
            ws.column_dimensions[col_letter].width = width

        ws.row_dimensions[row].height = 30

        # 示例数据
        example_data = [
            'PC-2026-001', '联想ThinkPad X1', 'SN123456789', 'AA:BB:CC:DD:EE:FF',
            '192.168.1.100', '张三', '技术部', '2026-01-15', '在用',
            '联想集团', 8999.00, '2026-01-20'
        ]

        row = 4
        for col_idx, value in enumerate(example_data):
            col_letter = chr(65 + col_idx)
            cell = ws[f'{col_letter}{row}']
            cell.value = value
            cell.font = example_font
            cell.alignment = example_alignment
            cell.border = thin_border

        ws.row_dimensions[row].height = 25

        # 添加数据验证说明
        ws.merge_cells('A6:L6')
        help_cell = ws['A6']
        help_cell.value = '填写完成后，请删除示例行（第4行），然后导入数据。'
        help_cell.font = Font(name='微软雅黑', size=9, color='666666')
        help_cell.alignment = Alignment(horizontal='left', vertical='center')

        # 保存到内存
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        from flask import send_file
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='电脑资产导入模板.xlsx'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 导入电脑资产数据
@app.route('/api/computers/import', methods=['POST'])
@login_required
@permission_required('computer', 'edit')
def import_computers():
    try:
        from openpyxl import load_workbook

        if 'file' not in request.files:
            return jsonify({'error': '请选择文件'}), 400

        file = request.files['file']
        if not file.filename.endswith('.xlsx'):
            return jsonify({'error': '请上传xlsx格式的文件'}), 400

        wb = load_workbook(file)
        ws = wb.active

        # 读取表头（第3行）
        headers = []
        for col in range(1, 13):
            headers.append(ws.cell(row=3, column=col).value)

        # 状态映射
        status_map = {
            '在用': 'in_use',
            '库存': 'stock',
            '故障': 'fault'
        }

        imported = 0
        errors = []
        duplicates = []

        # 从第4行开始读取数据
        for row in range(4, ws.max_row + 1):
            # 跳过空行
            if not ws.cell(row=row, column=1).value:
                continue

            asset_no = str(ws.cell(row=row, column=1).value).strip()

            # 检查必填字段
            if not asset_no:
                errors.append(f'第{row}行：资产编号不能为空')
                continue

            # 检查是否重复
            if ComputerAsset.query.filter_by(asset_no=asset_no).first():
                duplicates.append(f'第{row}行：资产编号 {asset_no} 已存在')
                continue

            try:
                # 解析日期
                receive_date = None
                if ws.cell(row=row, column=8).value:
                    date_val = ws.cell(row=row, column=8).value
                    if isinstance(date_val, datetime):
                        receive_date = date_val.date()
                    else:
                        receive_date = datetime.strptime(str(date_val), '%Y-%m-%d').date()

                entry_date = None
                if ws.cell(row=row, column=12).value:
                    date_val = ws.cell(row=row, column=12).value
                    if isinstance(date_val, datetime):
                        entry_date = date_val.date()
                    else:
                        entry_date = datetime.strptime(str(date_val), '%Y-%m-%d').date()

                # 解析状态
                status_str = str(ws.cell(row=row, column=9).value or '在用').strip()
                status = status_map.get(status_str, 'in_use')

                # 解析金额
                entry_amount = None
                if ws.cell(row=row, column=11).value:
                    entry_amount = float(ws.cell(row=row, column=11).value)

                computer = ComputerAsset(
                    asset_no=asset_no,
                    asset_model=str(ws.cell(row=row, column=2).value or '').strip() or None,
                    serial_number=str(ws.cell(row=row, column=3).value or '').strip() or None,
                    mac_address=str(ws.cell(row=row, column=4).value or '').strip() or None,
                    ip_address=str(ws.cell(row=row, column=5).value or '').strip() or None,
                    user_name=str(ws.cell(row=row, column=6).value or '').strip() or None,
                    department=str(ws.cell(row=row, column=7).value or '').strip() or None,
                    receive_date=receive_date,
                    status=status,
                    supplier=str(ws.cell(row=row, column=10).value or '').strip() or None,
                    entry_amount=entry_amount,
                    entry_date=entry_date
                )
                db.session.add(computer)
                imported += 1
            except Exception as e:
                errors.append(f'第{row}行：数据格式错误 - {str(e)}')

        if imported > 0:
            db.session.commit()

        result = {
            'message': f'导入完成，成功导入 {imported} 条记录',
            'imported': imported
        }
        if errors:
            result['errors'] = errors[:10]  # 最多显示10条错误
            result['error_count'] = len(errors)
        if duplicates:
            result['duplicates'] = duplicates[:10]
            result['duplicate_count'] = len(duplicates)

        return jsonify(result)
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 下载设备资产导入模板
@app.route('/api/devices/template', methods=['GET'])
@login_required
@permission_required('device', 'edit')
def download_device_template():
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from io import BytesIO

        wb = Workbook()
        ws = wb.active
        ws.title = "设备资产导入模板"

        # 定义样式
        header_font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='CF0A2C', end_color='CF0A2C', fill_type='solid')
        header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        title_font = Font(name='微软雅黑', size=16, bold=True, color='CF0A2C')
        title_alignment = Alignment(horizontal='center', vertical='center')

        note_font = Font(name='微软雅黑', size=9, color='FF0000')
        note_alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

        example_font = Font(name='微软雅黑', size=10, color='999999')
        example_alignment = Alignment(horizontal='center', vertical='center')

        # 边框样式
        thin_border = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )

        # 标题行
        ws.merge_cells('A1:J1')
        title_cell = ws['A1']
        title_cell.value = '设备资产导入模板'
        title_cell.font = title_font
        title_cell.alignment = title_alignment
        ws.row_dimensions[1].height = 40

        # 说明行
        ws.merge_cells('A2:J2')
        note_cell = ws['A2']
        note_cell.value = '说明：带 * 号的字段为必填项；状态可选值：在用、库存、正常、故障；日期格式：YYYY-MM-DD（如：2026-01-15）'
        note_cell.font = note_font
        note_cell.alignment = note_alignment
        ws.row_dimensions[2].height = 30

        # 表头
        headers = [
            ('A', '资产编号 *', 15),
            ('B', '资产型号', 18),
            ('C', '序列号', 18),
            ('D', '使用人', 10),
            ('E', '使用部门', 12),
            ('F', '使用位置', 15),
            ('G', '状态', 8),
            ('H', '供应商', 20),
            ('I', '入账金额', 12),
            ('J', '入账日期', 12),
        ]

        row = 3
        for col_letter, header_name, width in headers:
            cell = ws[f'{col_letter}{row}']
            cell.value = header_name
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
            ws.column_dimensions[col_letter].width = width

        ws.row_dimensions[row].height = 30

        # 示例数据
        example_data = [
            'DEV-2026-001', '华为交换机S5720', 'SN987654321',
            '李四', '网络部', '3楼机房', '在用',
            '华为技术有限公司', 15000.00, '2026-02-01'
        ]

        row = 4
        for col_idx, value in enumerate(example_data):
            col_letter = chr(65 + col_idx)
            cell = ws[f'{col_letter}{row}']
            cell.value = value
            cell.font = example_font
            cell.alignment = example_alignment
            cell.border = thin_border

        ws.row_dimensions[row].height = 25

        # 添加数据验证说明
        ws.merge_cells('A6:J6')
        help_cell = ws['A6']
        help_cell.value = '填写完成后，请删除示例行（第4行），然后导入数据。'
        help_cell.font = Font(name='微软雅黑', size=9, color='666666')
        help_cell.alignment = Alignment(horizontal='left', vertical='center')

        # 保存到内存
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        from flask import send_file
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='设备资产导入模板.xlsx'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 导入设备资产数据
@app.route('/api/devices/import', methods=['POST'])
@login_required
@permission_required('device', 'edit')
def import_devices():
    try:
        from openpyxl import load_workbook

        if 'file' not in request.files:
            return jsonify({'error': '请选择文件'}), 400

        file = request.files['file']
        if not file.filename.endswith('.xlsx'):
            return jsonify({'error': '请上传xlsx格式的文件'}), 400

        wb = load_workbook(file)
        ws = wb.active

        # 读取表头（第3行）
        headers = []
        for col in range(1, 11):
            headers.append(ws.cell(row=3, column=col).value)

        # 状态映射
        status_map = {
            '在用': 'in_use',
            '库存': 'stock',
            '正常': 'normal',
            '故障': 'fault'
        }

        imported = 0
        errors = []
        duplicates = []

        # 从第4行开始读取数据
        for row in range(4, ws.max_row + 1):
            # 跳过空行
            if not ws.cell(row=row, column=1).value:
                continue

            asset_no = str(ws.cell(row=row, column=1).value).strip()

            # 检查必填字段
            if not asset_no:
                errors.append(f'第{row}行：资产编号不能为空')
                continue

            # 检查是否重复
            if DeviceAsset.query.filter_by(asset_no=asset_no).first():
                duplicates.append(f'第{row}行：资产编号 {asset_no} 已存在')
                continue

            try:
                # 解析日期
                entry_date = None
                if ws.cell(row=row, column=10).value:
                    date_val = ws.cell(row=row, column=10).value
                    if isinstance(date_val, datetime):
                        entry_date = date_val.date()
                    else:
                        entry_date = datetime.strptime(str(date_val), '%Y-%m-%d').date()

                # 解析状态
                status_str = str(ws.cell(row=row, column=7).value or '在用').strip()
                status = status_map.get(status_str, 'in_use')

                # 解析金额
                entry_amount = None
                if ws.cell(row=row, column=9).value:
                    entry_amount = float(ws.cell(row=row, column=9).value)

                device = DeviceAsset(
                    asset_no=asset_no,
                    asset_model=str(ws.cell(row=row, column=2).value or '').strip() or None,
                    serial_number=str(ws.cell(row=row, column=3).value or '').strip() or None,
                    user_name=str(ws.cell(row=row, column=4).value or '').strip() or None,
                    department=str(ws.cell(row=row, column=5).value or '').strip() or None,
                    location=str(ws.cell(row=row, column=6).value or '').strip() or None,
                    status=status,
                    supplier=str(ws.cell(row=row, column=8).value or '').strip() or None,
                    entry_amount=entry_amount,
                    entry_date=entry_date
                )
                db.session.add(device)
                imported += 1
            except Exception as e:
                errors.append(f'第{row}行：数据格式错误 - {str(e)}')

        if imported > 0:
            db.session.commit()

        result = {
            'message': f'导入完成，成功导入 {imported} 条记录',
            'imported': imported
        }
        if errors:
            result['errors'] = errors[:10]  # 最多显示10条错误
            result['error_count'] = len(errors)
        if duplicates:
            result['duplicates'] = duplicates[:10]
            result['duplicate_count'] = len(duplicates)

        return jsonify(result)
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 调拨API
@app.route('/api/transfer', methods=['POST'])
@login_required
def transfer_asset():
    try:
        data = request.json
        asset_type = data.get('asset_type')  # computer / device
        asset_id = data.get('asset_id')
        transfer_type = data.get('transfer_type')  # to_stock / to_user
        asset_status = data.get('status', 'normal')  # normal / fault（调拨到仓库时使用）

        if not asset_type or not asset_id or not transfer_type:
            return jsonify({'error': '参数不完整'}), 400

        # 检查权限
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 401

        if not user.is_admin:
            import json
            permissions = json.loads(user.permissions) if user.permissions else {}
            asset_permission = permissions.get(asset_type, 'none')
            if asset_permission != 'edit':
                return jsonify({'error': '没有编辑权限'}), 403

        # 获取资产
        if asset_type == 'computer':
            asset = ComputerAsset.query.get_or_404(asset_id)
        else:
            asset = DeviceAsset.query.get_or_404(asset_id)
        
        # 记录调拨
        record = TransferRecord(
            asset_type=asset_type,
            asset_no=asset.asset_no,
            transfer_type=transfer_type,
            target_user=data.get('target_user', ''),
            target_department=data.get('target_department', ''),
            target_location=data.get('target_location', ''),
            remark=data.get('remark', '')
        )
        db.session.add(record)
        
        # 更新资产信息
        if transfer_type == 'to_stock':
            asset.user_name = ''
            asset.department = ''
            asset.location = data.get('target_location', '仓库')
            asset.status = 'stock' if asset_status == 'normal' else 'fault'
        else:
            asset.user_name = data.get('target_user', '')
            asset.department = data.get('target_department', '')
            asset.location = data.get('target_location', '')
            asset.status = 'in_use'
        
        db.session.commit()
        return jsonify({'message': '调拨成功', 'record': record.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/transfer/records', methods=['GET'])
@login_required
def get_transfer_records():
    try:
        # 检查用户是否有查看任一资产类型的权限
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 401

        if not user.is_admin:
            import json
            permissions = json.loads(user.permissions) if user.permissions else {}
            computer_perm = permissions.get('computer', 'none')
            device_perm = permissions.get('device', 'none')
            if computer_perm == 'none' and device_perm == 'none':
                return jsonify({'error': '没有查看权限'}), 403

        records = TransferRecord.query.order_by(TransferRecord.created_at.desc()).all()
        return jsonify([r.to_dict() for r in records])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transfer/records/<asset_no>', methods=['GET'])
@login_required
def get_transfer_records_by_asset(asset_no):
    try:
        # 检查用户是否有查看任一资产类型的权限
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 401

        if not user.is_admin:
            import json
            permissions = json.loads(user.permissions) if user.permissions else {}
            computer_perm = permissions.get('computer', 'none')
            device_perm = permissions.get('device', 'none')
            if computer_perm == 'none' and device_perm == 'none':
                return jsonify({'error': '没有查看权限'}), 403

        records = TransferRecord.query.filter_by(asset_no=asset_no).order_by(TransferRecord.created_at.desc()).all()
        return jsonify([r.to_dict() for r in records])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 用户管理API（需要认证和管理员权限）
@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    try:
        # 检查管理员权限
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        users = User.query.all()
        return jsonify([u.to_dict() for u in users])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['POST'])
@login_required
def create_user():
    try:
        # 检查管理员权限
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        data = request.json

        # 检查用户名是否已存在
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400

        # 检查邮箱是否已存在
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400

        import json

        # 权限设置，默认为只读
        permissions = data.get('permissions', {
            'computer': 'readonly',
            'device': 'readonly'
        })

        # 验证权限值
        valid_permissions = ['none', 'readonly', 'edit']
        if permissions.get('computer') not in valid_permissions:
            return jsonify({'error': '无效的电脑资产权限值'}), 400
        if permissions.get('device') not in valid_permissions:
            return jsonify({'error': '无效的设备资产权限值'}), 400

        user = User(
            username=data['username'],
            email=data['email'],
            department=data.get('department'),
            position=data.get('position'),
            is_admin=data.get('is_admin', False),
            permissions=json.dumps(permissions)
        )

        if 'password' in data:
            user.set_password(data['password'])
        else:
            return jsonify({'error': 'Password is required'}), 400

        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:id>', methods=['PUT'])
@login_required
def update_user(id):
    try:
        # 检查管理员权限
        current_user = User.query.get(session['user_id'])
        if not current_user or not current_user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        user = User.query.get_or_404(id)
        data = request.json

        # 检查用户名是否已被其他人使用
        if 'username' in data and data['username'] != user.username:
            if User.query.filter_by(username=data['username']).first():
                return jsonify({'error': 'Username already exists'}), 400

        # 检查邮箱是否已被其他人使用
        if 'email' in data and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'Email already exists'}), 400

        import json

        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        user.department = data.get('department', user.department)
        user.position = data.get('position', user.position)

        # 更新权限
        if 'permissions' in data:
            # 验证权限值
            valid_permissions = ['none', 'readonly', 'edit']
            if data['permissions'].get('computer') not in valid_permissions:
                return jsonify({'error': '无效的电脑资产权限值'}), 400
            if data['permissions'].get('device') not in valid_permissions:
                return jsonify({'error': '无效的设备资产权限值'}), 400
            user.permissions = json.dumps(data['permissions'])

        # 不允许修改自己的管理员状态
        if id == current_user.id and 'is_admin' in data and not data['is_admin']:
            return jsonify({'error': '不能取消自己的管理员权限'}), 400

        user.is_admin = data.get('is_admin', user.is_admin)

        if 'password' in data and data['password']:
            user.set_password(data['password'])

        db.session.commit()
        return jsonify(user.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:id>', methods=['DELETE'])
@login_required
def delete_user(id):
    try:
        # 检查管理员权限
        current_user = User.query.get(session['user_id'])
        if not current_user or not current_user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        user = User.query.get_or_404(id)

        # 不允许删除管理员账号
        if user.username == 'admin':
            return jsonify({'error': 'Cannot delete admin account'}), 403

        # 不允许删除自己
        if id == current_user.id:
            return jsonify({'error': '不能删除自己的账号'}), 400

        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 设置API（需要认证）
@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    return jsonify({
        'language': 'zh-CN'
    })

@app.route('/api/settings', methods=['PUT'])
@login_required
def update_settings():
    data = request.json
    return jsonify({'message': 'Settings updated', 'settings': data})

# 资产入账字段配置API
@app.route('/api/asset-fields/<asset_type>', methods=['GET'])
@login_required
def get_asset_fields(asset_type):
    try:
        # 验证asset_type参数
        if asset_type not in ['computer', 'device']:
            return jsonify({'error': '无效的资产类型'}), 400

        fields = AssetFieldConfig.query.filter_by(asset_type=asset_type).order_by(AssetFieldConfig.order).all()
        # 如果没有配置数据，初始化默认配置
        if not fields:
            init_default_field_configs()
            fields = AssetFieldConfig.query.filter_by(asset_type=asset_type).order_by(AssetFieldConfig.order).all()
        return jsonify([f.to_dict() for f in fields])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/asset-fields/<asset_type>', methods=['PUT'])
@login_required
def update_asset_fields(asset_type):
    try:
        # 检查管理员权限
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        # 验证asset_type参数
        if asset_type not in ['computer', 'device']:
            return jsonify({'error': '无效的资产类型'}), 400

        data = request.json
        fields = data.get('fields', [])
        for field_data in fields:
            field = AssetFieldConfig.query.get(field_data['id'])
            if field:
                field.visible = field_data.get('visible', field.visible)
                field.required = field_data.get('required', field.required)
        db.session.commit()
        return jsonify({'message': '配置已保存'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def init_default_field_configs():
    """初始化默认字段配置"""
    try:
        default_fields = [
            # 电脑资产字段
            {'asset_type': 'computer', 'field_name': 'asset_no', 'field_label': '资产编号', 'visible': True, 'required': True, 'order': 1},
            {'asset_type': 'computer', 'field_name': 'asset_model', 'field_label': '资产型号', 'visible': True, 'required': False, 'order': 2},
            {'asset_type': 'computer', 'field_name': 'serial_number', 'field_label': '序列号', 'visible': True, 'required': False, 'order': 3},
            {'asset_type': 'computer', 'field_name': 'mac_address', 'field_label': 'MAC地址', 'visible': True, 'required': False, 'order': 4},
            {'asset_type': 'computer', 'field_name': 'ip_address', 'field_label': 'IP地址', 'visible': True, 'required': False, 'order': 5},
            {'asset_type': 'computer', 'field_name': 'user_name', 'field_label': '使用人', 'visible': True, 'required': False, 'order': 6},
            {'asset_type': 'computer', 'field_name': 'department', 'field_label': '使用部门', 'visible': True, 'required': False, 'order': 7},
            {'asset_type': 'computer', 'field_name': 'receive_date', 'field_label': '领用日期', 'visible': True, 'required': False, 'order': 8},
            {'asset_type': 'computer', 'field_name': 'supplier', 'field_label': '供应商', 'visible': True, 'required': False, 'order': 9},
            {'asset_type': 'computer', 'field_name': 'entry_amount', 'field_label': '入账金额', 'visible': True, 'required': False, 'order': 10},
            {'asset_type': 'computer', 'field_name': 'entry_date', 'field_label': '入账日期', 'visible': True, 'required': False, 'order': 11},
            {'asset_type': 'computer', 'field_name': 'remark', 'field_label': '备注', 'visible': True, 'required': False, 'order': 12},
            # 设备资产字段
            {'asset_type': 'device', 'field_name': 'asset_no', 'field_label': '资产编号', 'visible': True, 'required': True, 'order': 1},
            {'asset_type': 'device', 'field_name': 'asset_model', 'field_label': '资产型号', 'visible': True, 'required': False, 'order': 2},
            {'asset_type': 'device', 'field_name': 'serial_number', 'field_label': '序列号', 'visible': True, 'required': False, 'order': 3},
            {'asset_type': 'device', 'field_name': 'user_name', 'field_label': '使用人', 'visible': True, 'required': False, 'order': 4},
            {'asset_type': 'device', 'field_name': 'department', 'field_label': '使用部门', 'visible': True, 'required': False, 'order': 5},
            {'asset_type': 'device', 'field_name': 'location', 'field_label': '使用位置', 'visible': True, 'required': False, 'order': 6},
            {'asset_type': 'device', 'field_name': 'supplier', 'field_label': '供应商', 'visible': True, 'required': False, 'order': 7},
            {'asset_type': 'device', 'field_name': 'entry_amount', 'field_label': '入账金额', 'visible': True, 'required': False, 'order': 8},
            {'asset_type': 'device', 'field_name': 'entry_date', 'field_label': '入账日期', 'visible': True, 'required': False, 'order': 9},
            {'asset_type': 'device', 'field_name': 'remark', 'field_label': '备注', 'visible': True, 'required': False, 'order': 10},
        ]
        for field in default_fields:
            db.session.add(AssetFieldConfig(**field))
        db.session.commit()
        print("Default asset field configurations initialized")
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing field configs: {e}")

# 获取备份列表API（需要认证和管理员权限）
@app.route('/api/backups', methods=['GET'])
@login_required
def get_backups():
    try:
        # 检查管理员权限
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        backup_files = glob.glob(os.path.join(backup_dir, '*.db'))
        backup_files.sort(key=os.path.getmtime, reverse=True)

        backups = []
        for filepath in backup_files[:5]:  # 只返回最近5份
            filename = os.path.basename(filepath)
            stat = os.stat(filepath)
            backups.append({
                'filename': filename,
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created_at_display': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })

        return jsonify({'backups': backups})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 数据备份API（需要认证和管理员权限）
@app.route('/api/backup', methods=['POST'])
@login_required
def backup_data():
    try:
        # 检查管理员权限
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        db_path = os.path.join(data_dir, 'assets.db')

        if not os.path.exists(db_path):
            return jsonify({'error': '数据库文件不存在'}), 400

        # 统计当前数据
        computer_count = ComputerAsset.query.count()
        device_count = DeviceAsset.query.count()

        # 生成备份文件名
        now = datetime.now()
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        backup_filename = f'assets_backup_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)

        # 复制数据库文件（使用copy而不是copy2，避免保留源文件时间戳）
        shutil.copy(db_path, backup_path)

        # 更新备份文件的修改时间为当前时间
        os.utime(backup_path, (now.timestamp(), now.timestamp()))

        # 清理旧备份，只保留最近5份
        backup_files = glob.glob(os.path.join(backup_dir, '*.db'))
        backup_files.sort(key=os.path.getmtime, reverse=True)

        for old_backup in backup_files[5:]:
            os.remove(old_backup)

        return jsonify({
            'message': '备份成功',
            'filename': backup_filename,
            'computer_count': computer_count,
            'device_count': device_count,
            'created_at_display': now.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 数据恢复API（需要认证和管理员权限）
@app.route('/api/restore', methods=['POST'])
@login_required
def restore_data():
    try:
        # 检查管理员权限
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        data = request.json
        filename = data.get('filename')

        if not filename:
            return jsonify({'error': '请选择备份文件'}), 400

        backup_path = os.path.join(backup_dir, filename)

        if not os.path.exists(backup_path):
            return jsonify({'error': '备份文件不存在'}), 400

        # 防止路径遍历攻击
        if not os.path.abspath(backup_path).startswith(os.path.abspath(backup_dir)):
            return jsonify({'error': '无效的备份文件路径'}), 400

        db_path = os.path.join(data_dir, 'assets.db')

        # 关闭当前数据库连接
        db.session.close()
        db.engine.dispose()

        # 替换数据库文件
        shutil.copy2(backup_path, db_path)

        return jsonify({
            'message': '恢复成功，系统将自动刷新'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)