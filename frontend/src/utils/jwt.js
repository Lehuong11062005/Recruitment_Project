/**
 * Giải mã payload của JWT Token (không cần thư viện ngoài, hỗ trợ UTF-8)
 * @param {string} token
 * @returns {Object|null}
 */
export const decodeToken = (token) => {
  if (!token || typeof token !== 'string') return null;
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');

    const jsonPayload = decodeURIComponent(
      atob(padded)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );

    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
};

// Export thêm alias parseJwt phòng trường hợp các file cũ của Hùng đang gọi tên này
export const parseJwt = decodeToken;

/**
 * Kiểm tra xem JWT Token đã hết hạn hay chưa (dựa trên claim exp)
 * @param {string} token
 * @returns {boolean}
 */
export const isTokenExpired = (token) => {
  const payload = decodeToken(token);
  if (!payload) return true;
  if (!payload.exp) return false;

  const nowInSeconds = Math.floor(Date.now() / 1000);
  return payload.exp <= nowInSeconds;
};

/**
 * Lấy thông tin user cơ bản từ JWT Token
 * @param {string} token
 * @returns {Object|null}
 */
export const getUserFromToken = (token) => {
  const payload = decodeToken(token);
  if (!payload) return null;
  return {
    id: payload.sub || payload.id,
    email: payload.email,
    role: payload.role,
  };
};

export default {
  decodeToken,
  parseJwt,
  isTokenExpired,
  getUserFromToken,
};