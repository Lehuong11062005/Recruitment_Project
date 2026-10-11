export const ROLES = {
  CANDIDATE: 'CANDIDATE',
  RECRUITER: 'RECRUITER',
  ADMIN: 'ADMIN',
}

// Trang chủ sau khi đăng nhập của từng vai trò
export const ROLE_HOME = {
  [ROLES.CANDIDATE]: '/candidate',
  [ROLES.RECRUITER]: '/recruiter',
  [ROLES.ADMIN]: '/admin',
}

/**
 * Backend trả user: { role: "USER" | "ADMIN", user_type: "CANDIDATE" | "RECRUITER" | null }
 * Quy ước giống get_role_claim() của core-service: ADMIN nếu role = ADMIN, ngược lại lấy user_type.
 */
export function getUserRole(user) {
  if (!user) return null
  if (user.role === ROLES.ADMIN) return ROLES.ADMIN
  return user.user_type ?? null
}
