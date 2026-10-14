import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

export default function DashboardLayout({ roleLabel, navItems = [] }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', backgroundColor: '#F5F8FC' }}>
      {/* Sidebar màu Navy #142B4A */}
      <aside
        style={{
          width: '250px',
          backgroundColor: '#142B4A',
          color: '#FFFFFF',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          padding: '24px 16px',
          flexShrink: 0,
        }}
      >
        <div>
          <div style={{ padding: '0 12px 20px', borderBottom: '1px solid rgba(255,255,255,0.12)' }}>
            <div style={{ fontSize: '16px', fontWeight: 700, color: '#FFFFFF' }}>
              Smart Recruitment
            </div>
            <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '4px' }}>
              {roleLabel}
            </div>
          </div>

          <nav style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                style={({ isActive }) => ({
                  padding: '10px 12px',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: 500,
                  color: '#FFFFFF',
                  textDecoration: 'none',
                  backgroundColor: isActive ? '#155EEF' : 'transparent',
                })}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        <div style={{ borderTop: '1px solid rgba(255,255,255,0.12)', paddingTop: '16px' }}>
          <div style={{ fontSize: '13px', fontWeight: 600, color: '#FFFFFF', padding: '0 8px' }}>
            {user?.full_name || user?.email}
          </div>
          <div style={{ fontSize: '12px', color: '#94A3B8', padding: '2px 8px 12px' }}>
            {user?.email}
          </div>
          <button
            type="button"
            onClick={handleLogout}
            style={{
              width: '100%',
              height: '38px',
              backgroundColor: 'transparent',
              color: '#FFFFFF',
              border: '1px solid rgba(255,255,255,0.25)',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Đăng xuất
          </button>
        </div>
      </aside>

      {/* Khu vực nội dung chính */}
      <main style={{ flex: 1, padding: '28px 32px', overflowY: 'auto' }}>
        <Outlet />
      </main>
    </div>
  );
}