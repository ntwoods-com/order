import React from "react";
import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import { useTheme as useCustomTheme } from "../auth/ThemeContext.jsx";
import * as api from "../api/client.js";
import {
  AppBar,
  Box,
  Toolbar,
  IconButton,
  Typography,
  Button,
  Container,
  Avatar,
  Menu,
  MenuItem,
  Divider,
  ListItemIcon,
  Chip,
  useMediaQuery,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
} from "@mui/material";
import {
  Menu as MenuIcon,
  Dashboard,
  AddCircle,
  Edit,
  Search,
  Receipt,
  AdminPanelSettings,
  Logout,
  LightMode,
  DarkMode,
  Person,
  Badge,
  Assignment,
} from "@mui/icons-material";
import { useTheme } from "@mui/material/styles";

export default function Layout() {
  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useCustomTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [anchorEl, setAnchorEl] = React.useState(null);
  const [mobileOpen, setMobileOpen] = React.useState(false);

  const handleUserMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    handleUserMenuClose();
    try {
      await api.logout();
    } catch {
      // ignore
    }
    logout();
    navigate("/login", { replace: true });
  };

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const navItems = [
    { path: "/dashboard", label: "Dashboard", icon: <Dashboard fontSize="small" /> },
    { path: "/new/upload", label: "New Order", icon: <AddCircle fontSize="small" /> },
    { path: "/additional/upload", label: "Additional", icon: <Edit fontSize="small" /> },
    { path: "/orders", label: "My Orders", icon: <Receipt fontSize="small" /> },
    { path: "/search", label: "Search", icon: <Search fontSize="small" /> },
    { path: "/order-id", label: "Order IDs", icon: <Badge fontSize="small" /> },
    { path: "/issue-order-id", label: "Issue ID", icon: <Assignment fontSize="small" /> },
    ...(user?.is_admin ? [{ path: "/admin", label: "Admin", icon: <AdminPanelSettings fontSize="small" /> }] : []),
  ];

  const drawer = (
    <Box sx={{ pt: 2 }}>
      <List>
        {navItems.map((item) => (
          <ListItem key={item.path} disablePadding>
            <ListItemButton
              component={NavLink}
              to={item.path}
              selected={location.pathname === item.path}
              onClick={handleDrawerToggle}
              sx={{
                borderRadius: 1,
                mx: 1,
                '&.Mui-selected': {
                  bgcolor: 'primary.main',
                  color: 'white',
                  '&:hover': {
                    bgcolor: 'primary.dark',
                  },
                },
              }}
            >
              <ListItemIcon sx={{ color: 'inherit', minWidth: 40 }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="sticky" elevation={1} sx={{ bgcolor: 'background.paper', color: 'text.primary' }}>
        <Toolbar>
          {isMobile && (
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
          )}

          <Typography
            variant="h6"
            component="div"
            sx={{
              fontWeight: 700,
              background: 'linear-gradient(135deg, #3b82f6 0%, #7c3aed 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              mr: 4,
            }}
          >
            📦 Sale Order System
          </Typography>

          {!isMobile && (
            <Box sx={{ display: 'flex', gap: 1, flexGrow: 1 }}>
              {navItems.map((item) => (
                <Button
                  key={item.path}
                  component={NavLink}
                  to={item.path}
                  startIcon={item.icon}
                  variant={location.pathname === item.path ? "contained" : "text"}
                  size="small"
                  sx={{
                    textTransform: 'none',
                    color: location.pathname === item.path ? 'white' : 'text.secondary',
                  }}
                >
                  {item.label}
                </Button>
              ))}
            </Box>
          )}

          <Box sx={{ flexGrow: 1 }} />

          <IconButton onClick={toggleTheme} sx={{ mr: 1 }}>
            {isDark ? <LightMode /> : <DarkMode />}
          </IconButton>

          <Chip
            avatar={<Avatar sx={{ bgcolor: 'primary.main' }}><Person /></Avatar>}
            label={user?.username}
            onClick={handleUserMenuOpen}
            sx={{ cursor: 'pointer' }}
          />

          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleUserMenuClose}
            PaperProps={{
              elevation: 4,
              sx: { width: 200, mt: 1.5 },
            }}
          >
            <MenuItem disabled>
              <ListItemIcon>
                <Person fontSize="small" />
              </ListItemIcon>
              {user?.username}
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleLogout}>
              <ListItemIcon>
                <Logout fontSize="small" color="error" />
              </ListItemIcon>
              Logout
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      {isMobile && (
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: 240 },
          }}
        >
          {drawer}
        </Drawer>
      )}

      <Container
        maxWidth="xl"
        sx={{
          flexGrow: 1,
          py: 4,
          px: { xs: 2, sm: 3 },
        }}
      >
        <Outlet />
      </Container>
    </Box>
  );
}
