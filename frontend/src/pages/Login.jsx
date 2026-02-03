import React from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  Container,
  Avatar,
  Stack,
} from "@mui/material";
import { Login as LoginIcon, Person, Lock } from "@mui/icons-material";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (user) navigate("/dashboard", { replace: true });
  }, [user, navigate]);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(username.trim(), password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err?.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: 2,
      }}
    >
      <Container maxWidth="sm">
        <Card
          elevation={24}
          sx={{
            borderRadius: 4,
            overflow: 'visible',
          }}
        >
          <CardContent sx={{ p: 5 }}>
            <Stack spacing={3} alignItems="center">
              {/* Logo/Icon */}
              <Avatar
                sx={{
                  width: 80,
                  height: 80,
                  bgcolor: 'primary.main',
                  boxShadow: '0 8px 16px rgba(59, 130, 246, 0.3)',
                }}
              >
                <LoginIcon sx={{ fontSize: 40 }} />
              </Avatar>

              {/* Title */}
              <Box textAlign="center">
                <Typography variant="h4" fontWeight="bold" gutterBottom>
                  Sale Order System
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Sign in to your account to continue
                </Typography>
                <Typography variant="caption" color="text.secondary" mt={1} display="block">
                  Designed & Developed by Rajesh Jadoun
                </Typography>
              </Box>

              {/* Error Alert */}
              {error && (
                <Alert severity="error" sx={{ width: '100%' }}>
                  {error}
                </Alert>
              )}

              {/* Form */}
              <Box component="form" onSubmit={onSubmit} sx={{ width: '100%' }}>
                <Stack spacing={2.5}>
                  <TextField
                    fullWidth
                    label="Username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                    placeholder="Enter your username"
                    disabled={busy}
                    InputProps={{
                      startAdornment: <Person sx={{ mr: 1, color: 'action.active' }} />,
                    }}
                    required
                  />

                  <TextField
                    fullWidth
                    type="password"
                    label="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    placeholder="Enter your password"
                    disabled={busy}
                    InputProps={{
                      startAdornment: <Lock sx={{ mr: 1, color: 'action.active' }} />,
                    }}
                    required
                  />

                  <Button
                    type="submit"
                    variant="contained"
                    size="large"
                    fullWidth
                    disabled={busy}
                    sx={{ mt: 2, py: 1.5 }}
                  >
                    {busy ? "Signing in..." : "Sign In"}
                  </Button>
                </Stack>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
}
