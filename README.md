# OpenFGA ファイングレインド認可システム

OpenFGAを使用したRelationship-based Access Control (ReBAC) システムの実装例です。従来のRole-based Access Control (RBAC) とReBAC を組み合わせて、柔軟で細かい粒度の認可システムを構築しています。

## 🏗️ アーキテクチャ概要

このシステムは以下の3つの層で構成されています：

```
┌─────────────────┐
│   Frontend      │ React + TypeScript
│   (Port 5173)   │
└─────────────────┘
         │
┌─────────────────┐
│   Backend API   │ FastAPI + Python
│   (Port 8000)   │ 
└─────────────────┘
         │
┌─────────────────┐  ┌─────────────────┐
│   SQLite DB     │  │   OpenFGA       │
│  (リソース情報)   │  │  (権限関係)      │
└─────────────────┘  └─────────────────┘
```

### データ分離設計

- **SQLite**: リソースの基本情報（ID、名前、所有者など）
- **OpenFGA**: 権限関係のタプル（ユーザー × リソース × 関係性）

## 🚀 セットアップ

### 環境要件

- Python 3.13.0
- Node.js 23.10.0  
- Docker 28.0.1
- FastAPI 0.116.1
- React 19.1.1

### 1. OpenFGAサーバーの起動

```bash
# OpenFGAサーバーをDockerで起動
docker run -p 8080:8080 openfga/openfga:latest run
```

### 2. バックエンドセットアップ

```bash
# 仮想環境作成
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係インストール
pip install fastapi uvicorn openfga-sdk sqlalchemy python-dotenv

# 環境変数設定
cp .env.example .env
# .envファイルを編集して適切な値を設定

# OpenFGAストアとモデル作成
python setup_fga.py

# サーバー起動
uvicorn main:app --reload
```

### 3. フロントエンドセットアップ

```bash
cd frontend

# 依存関係インストール
npm install

# 開発サーバー起動
npm run dev
```

## 📊 権限モデル

### OpenFGA認可モデル

```yaml
model
  schema 1.1

type user

type resource
  relations
    define owner: [user]
    define editor: [user]
    define viewer: [user] or editor or owner
```

### 権限の階層構造

```
owner (所有者)
  └── editor (編集者) 
      └── viewer (閲覧者)
```

- **owner**: 全ての操作が可能（作成・読取・更新・削除・共有）
- **editor**: 編集操作が可能（作成・読取・更新）+ viewer権限継承
- **viewer**: 読取のみ可能 + editor/owner権限継承

## 🔑 認可システムの仕組み

### 1. リソース作成時

```python
# 1. SQLiteにリソース情報保存
new_resource = Resource(name="企画書", owner="alice@example.com")
db.add(new_resource)
db.commit()

# 2. OpenFGAに権限タプル追加
write_request = ClientWriteRequest(
    writes=[ClientTuple(
        user="user:alice@example.com",
        relation="owner",
        object=f"resource:{new_resource.uuid}"
    )]
)
await fga_client.write(write_request)
```

### 2. 権限チェック時

```python
# OpenFGAで権限確認
check_request = ClientCheckRequest(
    user="user:bob@example.com",
    relation="viewer", 
    object="resource:abc-123-def"
)
response = await fga_client.check(check_request)

if response.allowed:
    return resource  # アクセス許可
else:
    raise HTTPException(status_code=403)  # アクセス拒否
```

### 3. 権限共有時

```python
# 特定ユーザーにビューアー権限付与
share_request = ClientWriteRequest(
    writes=[ClientTuple(
        user="user:bob@example.com",
        relation="viewer",
        object="resource:abc-123-def"
    )]
)
await fga_client.write(share_request)
```

## 🛡️ ハイブリッド認可（RBAC + ReBAC）

### RBAC（ロールベース）- デフォルト権限

```python
ROLE_PERMISSIONS = {
    "admin": ["create", "read", "update", "delete"],    # 全権限
    "editor": ["create", "read", "update"],             # 編集権限
    "viewer": ["read"],                                 # 閲覧権限
    "guest": []                                         # 権限なし
}
```

### ReBAC（関係ベース）- 個別権限

```python
# OpenFGAに保存される個別の権限関係
user:bob@example.com owner resource:important-doc     # bobに特定文書の所有権
user:charlie@example.com viewer resource:public-doc   # charlieに特定文書の閲覧権
```

### 権限判定フロー

```python
@require_permission("delete", "owner")
async def delete_resource(resource_uuid: str, user_email: str):
    # 1. RBAC: ユーザーロールに"delete"権限があるか？
    if has_role_permission(user_email, "delete"):
        return await delete_from_db(resource_uuid)
    
    # 2. ReBAC: このリソースの"owner"関係があるか？
    if await has_resource_permission(user_email, resource_uuid, "owner"):
        return await delete_from_db(resource_uuid)
    
    # 3. どちらもダメなら拒否
    raise HTTPException(status_code=403)
```

## 📡 API エンドポイント

### リソース管理

#### `POST /api/v1/resources`
新しいリソースを作成し、作成者をownerとして設定

**リクエスト:**
```json
{
  "name": "企画書"
}
```

**レスポンス:**
```json
{
  "id": 1,
  "uuid": "abc-123-def",
  "name": "企画書",
  "owner": "alice@example.com"
}
```

#### `GET /api/v1/resources`
ユーザーがアクセス可能なリソース一覧を取得

**レスポンス:**
```json
[
  {
    "id": 1,
    "uuid": "abc-123-def", 
    "name": "企画書",
    "owner": "alice@example.com"
  }
]
```

#### `GET /api/v1/resources/{resource_uuid}`
特定リソースの詳細を取得（viewer権限以上が必要）

#### `POST /api/v1/resources/{resource_uuid}/share`
リソースを他のユーザーと共有（owner権限が必要）

**リクエスト:**
```json
{
  "user_email": "bob@example.com",
  "relation": "viewer"
}
```

#### `DELETE /api/v1/resources/{resource_uuid}`
リソースを削除（owner権限が必要）

### ユーザー管理

#### `GET /api/v1/users/me`
現在のユーザー情報を取得

#### `GET /api/v1/health`
システムの健全性チェック

## 🗂️ プロジェクト構成

```
rebac_auth/
├── app/
│   ├── __init__.py
│   ├── models.py           # SQLAlchemyモデル
│   ├── routes.py           # FastAPIルート
│   ├── schemas.py          # Pydanticスキーマ
│   ├── auth_decorators.py  # 認可デコレータ
│   └── hybrid_auth.py      # RBAC+ReBAC実装
├── frontend/               # React フロントエンド
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── config.py              # 設定とDB接続
├── main.py                # FastAPIアプリケーション
├── setup_fga.py          # OpenFGAセットアップスクリプト
├── .env                   # 環境変数
└── README.md
```

## 🎨 デコレータ実装例

### 認可デコレータの使用方法

`app/auth_decorators.py`で定義されたデコレータを使用して、簡潔な権限チェックを実現：

```python
from app.auth_decorators import require_permission, check_resource_permission

# 個別リソースアクセス - viewer権限が必要
@router.get("/resources/{resource_uuid}")
@require_permission("viewer")
async def get_resource(
    resource_uuid: str,
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resource = db.query(Resource).filter(Resource.uuid == resource_uuid).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource

# リソース削除 - owner権限が必要
@router.delete("/resources/{resource_uuid}")
@require_permission("owner")
async def delete_resource(
    resource_uuid: str,
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resource = db.query(Resource).filter(Resource.uuid == resource_uuid).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    db.delete(resource)
    db.commit()
    return {"message": "Resource deleted successfully"}

# リソース一覧 - ヘルパー関数を使用
@router.get("/resources")
async def list_resources(
    user_email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resources = db.query(Resource).all()
    accessible_resources = []
    
    for resource in resources:
        # 各リソースに対して権限チェック
        if await check_resource_permission(user_email, str(resource.uuid), "viewer"):
            accessible_resources.append(resource)
    
    return accessible_resources
```

### デコレータの利点

**Before（従来の実装）:**
```python
@router.get("/resources/{resource_uuid}")
async def get_resource(resource_uuid: str, user_email: str, db: Session):
    # 20行のボイラープレートコード
    resource = db.query(Resource).filter(Resource.uuid == resource_uuid).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    check_request = ClientCheckRequest(
        user=f"user:{user_email}",
        relation="viewer",
        object=f"resource:{resource.uuid}",
    )
    try:
        response = await fga_client.check(check_request)
        if not response.allowed:
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FGA check failed: {str(e)}")

    return resource
```

**After（デコレータ使用）:**
```python
@router.get("/resources/{resource_uuid}")
@require_permission("viewer")  # 1行で権限チェック完了
async def get_resource(resource_uuid: str, user_email: str, db: Session):
    resource = db.query(Resource).filter(Resource.uuid == resource_uuid).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource
```

**改善点:**
- **コード量**: 20行 → 1行（95%削減）
- **可読性**: 権限要件が一目で分かる
- **保守性**: 権限ロジックが一箇所に集約
- **再利用性**: 他のエンドポイントでも同じデコレータを使用可能
- **テスト性**: デコレータ単体でのテストが可能

## 🔧 設定ファイル

### .env

```bash
# OpenFGA設定
FGA_API_URL=http://localhost:8080
FGA_STORE_ID=your-store-id
FGA_MODEL_ID=your-model-id

# データベース設定
DATABASE_URL=sqlite:///db.sqlite3

# その他の設定
SECRET_KEY=your-secret-key
```

## 🎯 使用ケース

### 1. 文書管理システム

```python
# 文書作成者は自動的にowner
document = create_document("企画書.pdf", "alice@example.com")

# チームメンバーにeditor権限付与
share_document(document.uuid, "bob@example.com", "editor")

# 外部関係者にviewer権限付与  
share_document(document.uuid, "external@company.com", "viewer")
```

### 2. プロジェクト管理

```python
# プロジェクトリーダーがプロジェクト作成
project = create_project("新商品開発", "manager@company.com")

# 開発メンバーにeditor権限
for dev in developers:
    share_project(project.uuid, dev.email, "editor")

# ステークホルダーにviewer権限
for stakeholder in stakeholders:
    share_project(project.uuid, stakeholder.email, "viewer")
```

### 3. 階層的な権限管理

```python
# 部長は全リソースにadminロール（RBAC）
user_roles["director@company.com"] = ["admin"]

# 特定プロジェクトのみ外部コンサルタントにeditor権限（ReBAC）
grant_permission("consultant@external.com", "special-project", "editor")
```

## 🚦 権限チェックの最適化

### バッチチェック

```python
# 複数リソースの権限を一括チェック
batch_request = BatchCheckRequest(
    items=[
        BatchCheckItem(user="user:alice", relation="viewer", object="resource:1"),
        BatchCheckItem(user="user:alice", relation="viewer", object="resource:2"),
        BatchCheckItem(user="user:alice", relation="viewer", object="resource:3"),
    ]
)
response = await fga_client.batch_check(batch_request)
```

### キャッシュ戦略

```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=1000)
async def cached_permission_check(user: str, relation: str, resource: str):
    """権限チェック結果を短時間キャッシュ"""
    result = await fga_client.check(...)
    return result.allowed

# TTLキャッシュの実装例
permission_cache = {}

async def check_with_ttl_cache(user, relation, resource, ttl_seconds=300):
    cache_key = f"{user}:{relation}:{resource}"
    now = datetime.now()
    
    if cache_key in permission_cache:
        cached_result, timestamp = permission_cache[cache_key]
        if now - timestamp < timedelta(seconds=ttl_seconds):
            return cached_result
    
    result = await fga_client.check(...)
    permission_cache[cache_key] = (result.allowed, now)
    return result.allowed
```

## 📈 パフォーマンス考慮事項

### 1. N+1クエリ問題の回避

```python
# ❌ 悪い例: リソースごとに個別チェック
async def list_resources_slow(user_email: str):
    resources = db.query(Resource).all()
    accessible = []
    for resource in resources:  # N+1クエリ発生
        if await check_permission(user_email, resource.uuid, "viewer"):
            accessible.append(resource)
    return accessible

# ✅ 良い例: バッチチェック使用
async def list_resources_fast(user_email: str):
    resources = db.query(Resource).all()
    
    # 一括で権限チェック
    batch_items = [
        BatchCheckItem(user=f"user:{user_email}", relation="viewer", object=f"resource:{r.uuid}")
        for r in resources
    ]
    batch_response = await fga_client.batch_check(BatchCheckRequest(items=batch_items))
    
    # 結果をマージ
    accessible = [
        resources[i] for i, item in enumerate(batch_response.result)
        if item.allowed
    ]
    return accessible
```

### 2. インデックスの活用

```python
# OpenFGAでのクエリ最適化のため、適切な関係性設計が重要
# viewer関係を継承可能に設計することで、クエリ効率が向上

type resource
  relations
    define owner: [user]
    define editor: [user] 
    define viewer: [user] or editor or owner  # 継承により効率的なクエリが可能
```

## 🔒 セキュリティベストプラクティス

### 1. 入力検証

```python
from pydantic import BaseModel, validator
import uuid

class ResourceCreate(BaseModel):
    name: str
    
    @validator('name')
    def name_must_be_valid(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('リソース名は必須です')
        if len(v) > 255:
            raise ValueError('リソース名は255文字以内である必要があります')
        return v.strip()

class ShareRequest(BaseModel):
    user_email: str
    relation: str = "viewer"
    
    @validator('user_email')
    def email_must_be_valid(cls, v):
        if '@' not in v:
            raise ValueError('有効なメールアドレスを入力してください')
        return v
    
    @validator('relation')
    def relation_must_be_valid(cls, v):
        if v not in ['owner', 'editor', 'viewer']:
            raise ValueError('無効な権限関係です')
        return v
```

### 2. エラーハンドリング

```python
import logging

logger = logging.getLogger(__name__)

async def safe_permission_check(user: str, relation: str, resource: str) -> bool:
    """安全な権限チェック（例外処理付き）"""
    try:
        response = await fga_client.check(...)
        return response.allowed
    except Exception as e:
        logger.error(f"Permission check failed: {user}, {relation}, {resource}, {str(e)}")
        # セキュリティ上、デフォルトは拒否
        return False
```

### 3. 監査ログ

```python
async def audit_log_permission_check(user: str, action: str, resource: str, allowed: bool):
    """権限チェック結果の監査ログ"""
    log_entry = {
        "timestamp": datetime.utcnow(),
        "user": user,
        "action": action, 
        "resource": resource,
        "allowed": allowed,
        "ip_address": request.client.host
    }
    
    # 監査ログDB、ファイル、またはログ集約システムに保存
    logger.info(f"AUDIT: {log_entry}")
```

## 🧪 テスト

### 単体テスト例

```python
import pytest
from app.hybrid_auth import has_role_permission, require_permission

def test_role_permission():
    """RBAC権限テスト"""
    assert has_role_permission("admin@company.com", "delete") == True
    assert has_role_permission("viewer@company.com", "delete") == False
    assert has_role_permission("editor@company.com", "update") == True

@pytest.mark.asyncio
async def test_resource_permission():
    """ReBAC権限テスト"""
    # テスト用のモックFGAクライアント設定
    resource_uuid = "test-resource-123"
    
    # owner権限のテスト
    result = await has_resource_permission(
        "alice@example.com", 
        resource_uuid, 
        "owner"
    )
    assert result == True
    
    # viewer権限のテスト
    result = await has_resource_permission(
        "bob@example.com",
        resource_uuid,
        "viewer" 
    )
    assert result == False
```

### 統合テスト例

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_resource():
    """リソース作成テスト"""
    response = client.post(
        "/api/v1/resources",
        json={"name": "テスト文書"},
        headers={"X-User-Email": "alice@example.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "テスト文書"
    assert data["owner"] == "alice@example.com"

def test_access_denied():
    """アクセス拒否テスト"""
    # 他人のリソースへのアクセス
    response = client.get(
        "/api/v1/resources/other-user-resource",
        headers={"X-User-Email": "bob@example.com"}
    )
    assert response.status_code == 403
```

## 📚 参考資料

### OpenFGA関連

- [OpenFGA公式ドキュメント](https://openfga.dev/docs)
- [OpenFGA Python SDK](https://github.com/openfga/python-sdk)
- [Zanzibar論文](https://research.google/pubs/pub48190/) - Googleの権限システムの論文

### 認可システム設計

- [NIST ABAC Guide](https://csrc.nist.gov/publications/detail/sp/800-162/final)
- [Auth0 RBAC vs ABAC](https://auth0.com/blog/role-based-access-control-rbac-and-attribute-based-access-control-abac/)

## 🤝 貢献

プルリクエストや Issue の報告を歓迎します！

### 開発環境セットアップ

```bash
# 開発用依存関係のインストール
pip install -r requirements-dev.txt

# コードフォーマット
black . && isort .

# 型チェック
mypy .

# テスト実行
pytest
```

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照してください。

---

## 💡 次のステップ

このプロジェクトを本格的に運用する場合の検討事項：

1. **認証システムの統合** - Auth0、Cognito、またはOIDC準拠システム
2. **権限モデルの拡張** - チーム、組織、プロジェクトなどの階層構造
3. **パフォーマンス監視** - OpenFGAクエリの監視とアラート
4. **権限変更の通知** - 権限付与/剥奪時の通知システム
5. **管理UI** - 権限管理用の管理画面
6. **監査機能** - 詳細な監査ログとレポート機能

このREADMEがOpenFGAとReBAC実装の参考になれば幸いです！🚀