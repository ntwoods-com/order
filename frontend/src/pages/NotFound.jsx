import React from "react";
import { Link } from "react-router-dom";
import { Box, Card, CardContent, Typography, Button } from "@mui/material";
import { Home, SentimentDissatisfied } from "@mui/icons-material";

export default function NotFound() {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
      <Card elevation={2} sx={{ maxWidth: 500 }}>
        <CardContent sx={{ textAlign: 'center', py: 6 }}>
          <SentimentDissatisfied sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }} />

          <Typography variant="h4" fontWeight="bold" gutterBottom>
            404 - Not Found
          </Typography>

          <Typography variant="body1" color="text.secondary" paragraph>
            This route does not exist. The page you are looking for might have been removed or is temporarily unavailable.
          </Typography>

          <Button
            component={Link}
            to="/dashboard"
            variant="contained"
            size="large"
            startIcon={<Home />}
            sx={{ mt: 2 }}
          >
            Go to Dashboard
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
}
