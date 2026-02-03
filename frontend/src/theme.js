import { createTheme } from '@mui/material/styles';

// Custom Material-UI theme with brand colors
const theme = createTheme({
    palette: {
        mode: 'light',
        primary: {
            main: '#3b82f6', // Blue 500
            light: '#60a5fa', // Blue 400
            dark: '#2563eb', // Blue 600
            contrastText: '#ffffff',
        },
        secondary: {
            main: '#7c3aed', // Purple 600
            light: '#a78bfa', // Purple 400
            dark: '#6d28d9', // Purple 700
            contrastText: '#ffffff',
        },
        error: {
            main: '#ef4444',
        },
        warning: {
            main: '#f59e0b',
        },
        success: {
            main: '#10b981',
        },
        background: {
            default: '#f3f4f6',
            paper: '#ffffff',
        },
        text: {
            primary: '#0f172a',
            secondary: '#475569',
        },
    },
    typography: {
        fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        h1: {
            fontWeight: 700,
            letterSpacing: '-0.025em',
        },
        h2: {
            fontWeight: 600,
            letterSpacing: '-0.025em',
        },
        h3: {
            fontWeight: 600,
            letterSpacing: '-0.025em',
        },
        button: {
            textTransform: 'none', // Don't uppercase buttons
            fontWeight: 600,
        },
    },
    shape: {
        borderRadius: 12,
    },
    shadows: [
        'none',
        '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
        '0 20px 40px -5px rgba(50, 50, 93, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)',
    ],
    components: {
        MuiButton: {
            styleOverrides: {
                root: {
                    borderRadius: 8,
                    padding: '10px 20px',
                },
                contained: {
                    boxShadow: '0 4px 15px rgba(59, 130, 246, 0.4)',
                    '&:hover': {
                        boxShadow: '0 8px 25px rgba(59, 130, 246, 0.6)',
                        transform: 'translateY(-2px)',
                    },
                },
            },
        },
        MuiCard: {
            styleOverrides: {
                root: {
                    borderRadius: 16,
                    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
                    '&:hover': {
                        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                        transform: 'translateY(-4px)',
                    },
                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                },
            },
        },
        MuiTextField: {
            styleOverrides: {
                root: {
                    '& .MuiOutlinedInput-root': {
                        borderRadius: 8,
                    },
                },
            },
        },
    },
});

export default theme;
