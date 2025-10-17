# Spec 3: Authentication & Authorization System

## Purpose
Implement secure JWT-based authentication with role-based access control (RBAC) for Owner, Receptionist, and Staff roles with specific permission boundaries.

## Scope
- User login/logout with JWT tokens
- Role-based permissions
- Session management with device binding for reception terminal
- Password hashing and security
- Privacy controls for staff users
- Audit logging for authentication events

## Security Requirements

### Password Policy
- Minimum 8 characters
- Must contain: uppercase, lowercase, number
- Bcrypt hashing with cost factor 12
- No password reuse (last 3 passwords)

### Token Strategy
- **Access Token**: Short-lived (15 minutes), JWT
- **Refresh Token**: Long-lived (7 days), stored in Redis
- **Device Binding**: Reception terminal gets persistent session
- **Rotation**: Refresh tokens rotate on use

### Session Management
- Redis-backed session store
- Automatic cleanup of expired sessions
- Device fingerprinting for reception terminal
- Manual logout clears all tokens

## Role Permissions Matrix

### Owner Role
```json
{
  "billing": {
    "create": true,
    "read": true,
    "update": true,
    "refund": true,
    "discount": true,
    "view_totals": true
  },
  "appointments": {
    "create": true,
    "read": true,
    "update": true,
    "delete": true,
    "assign_staff": true
  },
  "inventory": {
    "create": true,
    "read": true,
    "update": true,
    "approve_changes": true,
    "view_costs": true
  },
  "accounting": {
    "view_dashboard": true,
    "view_profit": true,
    "export_reports": true,
    "access_tax_reports": true
  },
  "staff": {
    "create": true,
    "read": true,
    "update": true,
    "delete": true
  },
  "settings": {
    "read": true,
    "update": true
  }
}
```

### Receptionist Role
```json
{
  "billing": {
    "create": true,
    "read": true,
    "update": false,
    "refund": false,
    "discount": true,
    "view_totals": true
  },
  "appointments": {
    "create": true,
    "read": true,
    "update": true,
    "delete": false,
    "assign_staff": true
  },
  "inventory": {
    "create": false,
    "read": true,
    "update": false,
    "request_changes": true,
    "view_costs": false
  },
  "accounting": {
    "view_dashboard": true,
    "view_profit": false,
    "open_close_drawer": true
  },
  "staff": {
    "read": true
  }
}
```

### Staff Role
```json
{
  "schedule": {
    "view_own": true,
    "view_all": true,
    "view_customer_name": "first_name_only",
    "view_phone": false
  },
  "services": {
    "mark_complete": true,
    "add_notes": true,
    "edit_notes_window_minutes": 15
  },
  "billing": {
    "view_totals": false
  }
}
```

## API Endpoints

### POST /api/auth/login
**Purpose**: Authenticate user and issue tokens

**Request Body**:
```json
{
  "username": "string",
  "password": "string",
  "device_id": "string (optional, for reception terminal)"
}
```

**Response (200)**:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "01HXXX...",
    "username": "owner",
    "full_name": "Salon Owner",
    "role": "owner",
    "permissions": { /* full permissions object */ }
  }
}
```

**Error Responses**:
- 401: Invalid credentials
- 403: Account disabled
- 429: Too many attempts (rate limited)

**Security Measures**:
- Rate limiting: 5 attempts per minute per IP
- Account lockout: 10 failed attempts locks for 15 minutes
- Audit log: All login attempts logged

### POST /api/auth/refresh
**Purpose**: Get new access token using refresh token

**Request Body**:
```json
{
  "refresh_token": "string"
}
```

**Response (200)**:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",  // New rotated token
  "expires_in": 900
}
```

**Error Responses**:
- 401: Invalid or expired refresh token
- 403: Token revoked or user disabled

### POST /api/auth/logout
**Purpose**: Invalidate tokens and end session

**Headers**:
```
Authorization: Bearer {access_token}
```

**Request Body**:
```json
{
  "refresh_token": "string (optional)",
  "logout_all_devices": false
}
```

**Response (200)**:
```json
{
  "message": "Logged out successfully"
}
```

**Behavior**:
- Removes refresh token from Redis
- Adds access token to blacklist (until expiry)
- If `logout_all_devices=true`, removes all user sessions

### GET /api/auth/me
**Purpose**: Get current user information

**Headers**:
```
Authorization: Bearer {access_token}
```

**Response (200)**:
```json
{
  "id": "01HXXX...",
  "username": "receptionist1",
  "full_name": "John Doe",
  "email": "john@salon.local",
  "role": "receptionist",
  "permissions": { /* permissions object */ },
  "last_login_at": "2025-10-15T10:30:00+05:30",
  "is_active": true
}
```

### POST /api/auth/change-password
**Purpose**: Change user's password

**Headers**:
```
Authorization: Bearer {access_token}
```

**Request Body**:
```json
{
  "current_password": "string",
  "new_password": "string"
}
```

**Response (200)**:
```json
{
  "message": "Password changed successfully"
}
```

**Validation**:
- Current password must be correct
- New password must meet policy requirements
- Cannot reuse last 3 passwords

## Implementation

### Backend Structure

```
backend/app/
├── auth/
│   ├── __init__.py
│   ├── dependencies.py      # FastAPI dependencies
│   ├── jwt.py               # JWT token handling
│   ├── password.py          # Password hashing/verification
│   ├── permissions.py       # Permission checking
│   └── router.py            # Auth endpoints
├── middleware/
│   ├── __init__.py
│   └── auth.py              # Authentication middleware
└── models/
    └── user.py              # User, Role models
```

### JWT Token Structure

**Access Token Payload**:
```json
{
  "sub": "01HXXX...",           // user_id
  "username": "owner",
  "role": "owner",
  "type": "access",
  "device_id": "reception_001",  // Optional
  "iat": 1697520000,
  "exp": 1697520900
}
```

**Refresh Token Payload**:
```json
{
  "sub": "01HXXX...",
  "type": "refresh",
  "device_id": "reception_001",
  "jti": "unique_token_id",      // For revocation
  "iat": 1697520000,
  "exp": 1698124800
}
```

### backend/app/auth/jwt.py

```python
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from app.config import settings
from app.models.user import User

class JWTHandler:
    """Handle JWT token creation and validation."""
    
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    @classmethod
    def create_access_token(
        cls,
        user: User,
        device_id: Optional[str] = None
    ) -> str:
        """Create JWT access token."""
        expire = datetime.utcnow() + timedelta(
            minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role.name.value,
            "type": "access",
            "iat": datetime.utcnow(),
            "exp": expire
        }
        
        if device_id:
            payload["device_id"] = device_id
        
        return jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=cls.ALGORITHM
        )
    
    @classmethod
    def create_refresh_token(
        cls,
        user: User,
        device_id: Optional[str] = None
    ) -> tuple[str, str]:
        """Create JWT refresh token. Returns (token, jti)."""
        from ulid import ULID
        
        jti = str(ULID())
        expire = datetime.utcnow() + timedelta(
            days=cls.REFRESH_TOKEN_EXPIRE_DAYS
        )
        
        payload = {
            "sub": user.id,
            "type": "refresh",
            "jti": jti,
            "iat": datetime.utcnow(),
            "exp": expire
        }
        
        if device_id:
            payload["device_id"] = device_id
        
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=cls.ALGORITHM
        )
        
        return token, jti
    
    @classmethod
    def decode_token(cls, token: str) -> Dict[str, Any]:
        """Decode and verify JWT token."""
        try:
            return jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[cls.ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
```

### backend/app/auth/password.py

```python
from passlib.context import CryptContext
from typing import List

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class PasswordHandler:
    """Handle password hashing and verification."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, List[str]]:
        """
        Validate password meets requirements.
        Returns (is_valid, error_messages)
        """
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        
        return len(errors) == 0, errors
```

### backend/app/auth/permissions.py

```python
from enum import Enum
from typing import Dict, Any
from app.models.user import RoleEnum

class Permission(str, Enum):
    """Permission constants."""
    # Billing
    CREATE_BILL = "billing.create"
    READ_BILL = "billing.read"
    REFUND_BILL = "billing.refund"
    APPLY_DISCOUNT = "billing.discount"
    VIEW_TOTALS = "billing.view_totals"
    
    # Appointments
    CREATE_APPOINTMENT = "appointments.create"
    READ_APPOINTMENT = "appointments.read"
    UPDATE_APPOINTMENT = "appointments.update"
    DELETE_APPOINTMENT = "appointments.delete"
    
    # Inventory
    APPROVE_INVENTORY_CHANGE = "inventory.approve"
    VIEW_COSTS = "inventory.view_costs"
    
    # Accounting
    VIEW_PROFIT = "accounting.view_profit"
    EXPORT_REPORTS = "accounting.export"
    
    # Staff
    MANAGE_USERS = "users.manage"

class PermissionChecker:
    """Check if user has required permissions."""
    
    ROLE_PERMISSIONS: Dict[RoleEnum, Dict[str, Any]] = {
        RoleEnum.OWNER: {
            "billing": ["create", "read", "update", "refund", "discount", "view_totals"],
            "appointments": ["create", "read", "update", "delete"],
            "inventory": ["create", "read", "update", "approve", "view_costs"],
            "accounting": ["view_dashboard", "view_profit", "export"],
            "users": ["create", "read", "update", "delete"],
            "settings": ["read", "update"]
        },
        RoleEnum.RECEPTIONIST: {
            "billing": ["create", "read", "discount", "view_totals"],
            "appointments": ["create", "read", "update"],
            "inventory": ["read", "request"],
            "accounting": ["view_dashboard", "manage_drawer"],
            "staff": ["read"]
        },
        RoleEnum.STAFF: {
            "schedule": ["view_all"],
            "services": ["mark_complete", "add_notes"],
            "pii_restrictions": ["first_name_only", "no_phone", "no_totals"]
        }
    }
    
    @classmethod
    def has_permission(
        cls,
        role: RoleEnum,
        resource: str,
        action: str
    ) -> bool:
        """Check if role has permission for resource.action."""
        role_perms = cls.ROLE_PERMISSIONS.get(role, {})
        resource_perms = role_perms.get(resource, [])
        return action in resource_perms
    
    @classmethod
    def can_view_customer_pii(cls, role: RoleEnum) -> bool:
        """Check if role can view full customer PII."""
        return role in [RoleEnum.OWNER, RoleEnum.RECEPTIONIST]
    
    @classmethod
    def can_view_financials(cls, role: RoleEnum) -> bool:
        """Check if role can view financial totals."""
        return role in [RoleEnum.OWNER, RoleEnum.RECEPTIONIST]
```

### backend/app/auth/dependencies.py

```python
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, RoleEnum
from app.auth.jwt import JWTHandler
from app.auth.permissions import PermissionChecker

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user."""
    try:
        token = credentials.credentials
        payload = JWTHandler.decode_token(token)
        
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        user = db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None),
            User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return user
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

def require_role(*allowed_roles: RoleEnum):
    """Dependency factory to require specific roles."""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role.name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker

def require_permission(resource: str, action: str):
    """Dependency factory to require specific permission."""
    def permission_checker(current_user: User = Depends(get_current_user)):
        if not PermissionChecker.has_permission(
            current_user.role.name,
            resource,
            action
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {resource}.{action}"
            )
        return current_user
    return permission_checker

# Commonly used dependencies
require_owner = require_role(RoleEnum.OWNER)
require_owner_or_receptionist = require_role(
    RoleEnum.OWNER,
    RoleEnum.RECEPTIONIST
)
```

### Session Management with Redis

```python
from typing import Optional
import redis.asyncio as redis
from datetime import timedelta
from app.config import settings

class SessionManager:
    """Manage user sessions in Redis."""
    
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)
    
    async def store_refresh_token(
        self,
        user_id: str,
        jti: str,
        token: str,
        device_id: Optional[str] = None
    ):
        """Store refresh token in Redis."""
        key = f"refresh_token:{user_id}:{jti}"
        
        data = {
            "token": token,
            "device_id": device_id or "unknown"
        }
        
        await self.redis.hset(key, mapping=data)
        await self.redis.expire(
            key,
            timedelta(days=JWTHandler.REFRESH_TOKEN_EXPIRE_DAYS)
        )
    
    async def validate_refresh_token(
        self,
        user_id: str,
        jti: str
    ) -> bool:
        """Check if refresh token exists and is valid."""
        key = f"refresh_token:{user_id}:{jti}"
        return await self.redis.exists(key) > 0
    
    async def revoke_refresh_token(self, user_id: str, jti: str):
        """Revoke a specific refresh token."""
        key = f"refresh_token:{user_id}:{jti}"
        await self.redis.delete(key)
    
    async def revoke_all_user_tokens(self, user_id: str):
        """Revoke all refresh tokens for a user."""
        pattern = f"refresh_token:{user_id}:*"
        async for key in self.redis.scan_iter(match=pattern):
            await self.redis.delete(key)
    
    async def blacklist_access_token(self, jti: str, expires_in: int):
        """Add access token to blacklist."""
        key = f"blacklist:{jti}"
        await self.redis.setex(key, expires_in, "1")
    
    async def is_token_blacklisted(self, jti: str) -> bool:
        """Check if access token is blacklisted."""
        key = f"blacklist:{jti}"
        return await self.redis.exists(key) > 0

session_manager = SessionManager()
```

## Frontend Integration

### Auth Context (React)

```typescript
// frontend/src/contexts/AuthContext.tsx
import { createContext, useContext, useState, useEffect } from 'react';

interface User {
  id: string;
  username: string;
  fullName: string;
  role: 'owner' | 'receptionist' | 'staff';
  permissions: Record<string, any>;
}

interface AuthContextType {
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  hasPermission: (resource: string, action: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  
  useEffect(() => {
    // Check for existing session on mount
    const token = localStorage.getItem('access_token');
    if (token) {
      fetchCurrentUser(token);
    }
  }, []);
  
  const login = async (username: string, password: string) => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    if (!response.ok) {
      throw new Error('Login failed');
    }
    
    const data = await response.json();
    
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    
    setAccessToken(data.access_token);
    setUser(data.user);
  };
  
  const logout = async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    
    await fetch('/api/auth/logout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ refresh_token: refreshToken })
    });
    
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setAccessToken(null);
    setUser(null);
  };
  
  const hasPermission = (resource: string, action: string): boolean => {
    if (!user?.permissions) return false;
    const resourcePerms = user.permissions[resource];
    return resourcePerms?.includes(action) ?? false;
  };
  
  return (
    <AuthContext.Provider value={{
      user,
      login,
      logout,
      isAuthenticated: !!user,
      hasPermission
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

### API Client with Token Refresh

```typescript
// frontend/src/lib/apiClient.ts
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

async function refreshAccessToken(): Promise<string> {
  const refreshToken = localStorage.getItem('refresh_token');
  
  const response = await fetch('/api/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken })
  });
  
  if (!response.ok) {
    // Refresh failed, redirect to login
    window.location.href = '/login';
    throw new Error('Token refresh failed');
  }
  
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  
  return data.access_token;
}

export async function apiRequest(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = localStorage.getItem('access_token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
    ...options.headers
  };
  
  let response = await fetch(url, { ...options, headers });
  
  // If 401, try refreshing token
  if (response.status === 401 && !isRefreshing) {
    isRefreshing = true;
    
    try {
      const newToken = await refreshAccessToken();
      
      // Retry original request with new token
      headers['Authorization'] = `Bearer ${newToken}`;
      response = await fetch(url, { ...options, headers });
      
      isRefreshing = false;
    } catch (error) {
      isRefreshing = false;
      throw error;
    }
  }
  
  return response;
}
```

## Acceptance Criteria

- [ ] User can login with username/password
- [ ] JWT access and refresh tokens issued on successful login
- [ ] Access token expires after 15 minutes
- [ ] Refresh token can get new access token
- [ ] Logout revokes refresh token in Redis
- [ ] Login attempts are rate limited (5/min)
- [ ] Account locks after 10 failed attempts for 15 minutes
- [ ] Owner has full system access
- [ ] Receptionist has limited access (no refunds, no profit view)
- [ ] Staff only sees first name + ticket number
- [ ] Staff cannot view billing totals
- [ ] Password must meet strength requirements
- [ ] Old passwords cannot be reused
- [ ] Device binding works for reception terminal
- [ ] All authentication events logged to audit_log
- [ ] Token blacklist prevents reuse of logged-out tokens
- [ ] API returns 401 for invalid/expired tokens
- [ ] API returns 403 for insufficient permissions

## Testing Checklist

```bash
# 1. Test login
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"owner","password":"change_me_123"}'

# 2. Test protected endpoint
curl http://localhost/api/auth/me \
  -H "Authorization: Bearer {access_token}"

# 3. Test refresh token
curl -X POST http://localhost/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"{refresh_token}"}'

# 4. Test logout
curl -X POST http://localhost/api/auth/logout \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"{refresh_token}"}'

# 5. Test rate limiting
for i in {1..10}; do
  curl -X POST http://localhost/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"owner","password":"wrong"}'
done
# Should get 429 after 5 attempts

# 6. Test permissions
# Login as staff user and try to access owner-only endpoint
curl http://localhost/api/accounting/profit \
  -H "Authorization: Bearer {staff_token}"
# Should get 403
```

## Next Steps
After authentication is validated:
1. Proceed to Spec 4: POS & Billing Module
2. Implement protected routes in frontend
3. Add permission checks to all API endpoints