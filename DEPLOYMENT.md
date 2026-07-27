# AgroScan NG - Render Deployment Guide

## Overview
This guide explains how to deploy the AgroScan NG application to Render.com. The application consists of:
- PostgreSQL Database
- Backend API (Flask)
- Frontend (React/Vite)
- Inference Service (TensorFlow ML Model)

## Prerequisites
- Render.com account
- GitHub repository with the project code
- Render CLI (optional, for command-line deployment)

## Deployment Strategy

### Option 1: Free Tier Deployment (Database + API + Frontend)
**Cost: $0/month**
- PostgreSQL Database (Free)
- Backend API (Free)
- Frontend (Free)
- **Note**: Inference service requires paid plan due to ML workload requirements

### Option 2: Full Deployment (All Services)
**Cost: ~$7/month (Starter plan for inference)**
- PostgreSQL Database (Free)
- Backend API (Free)
- Frontend (Free)
- Inference Service (Starter plan - $7/month)

## Deployment Steps

### Step 1: Prepare Your Repository
1. Push your code to GitHub
2. Ensure all Dockerfiles are present
3. Verify environment variable configurations

### Step 2: Deploy Database
1. Go to Render Dashboard
2. Click "New +" → "PostgreSQL"
3. Configure:
   - Name: `agroscan-db`
   - Database: `agroscan`
   - User: `agroscan`
   - Region: Oregon (or nearest to your users)
4. Click "Create Database"

### Step 3: Deploy Backend API
1. Go to Render Dashboard
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - Name: `agroscan-api`
   - Environment: Docker
   - Docker Context: `.`
   - Dockerfile Path: `api/Dockerfile`
   - Region: Oregon
5. Add Environment Variables:
   - `DATABASE_URL`: (from Render database connection string)
   - `INFERENCE_URL`: `https://agroscan-inference.onrender.com` (if deploying inference)
   - `JWT_SECRET`: (generate secure random string)
   - `ALLOWED_ORIGINS`: `https://agroscan-frontend.onrender.com`
   - `UPLOAD_DIR`: `/app/uploads/thumbnails`
   - `UPLOAD_URL_PREFIX`: `/api/v1/uploads/thumbnails`
6. Click "Create Web Service"

### Step 4: Deploy Frontend
1. Go to Render Dashboard
2. Click "New +" → "Static Site"
3. Connect your GitHub repository
4. Configure:
   - Name: `agroscan-frontend`
   - Build Command: `cd frontend && npm install && npm run build`
   - Publish Directory: `frontend/dist`
   - Region: Oregon
5. Add Environment Variables:
   - `VITE_API_BASE_URL`: `https://agroscan-api.onrender.com/api/v1`
6. Click "Create Static Site"

### Step 5: Deploy Inference Service (Optional - Requires Paid Plan)
1. Go to Render Dashboard
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - Name: `agroscan-inference`
   - Environment: Docker
   - Docker Context: `.`
   - Dockerfile Path: `inference/Dockerfile`
   - Plan: Starter ($7/month - required for ML workloads)
   - Region: Oregon
5. Add Environment Variables:
   - `MODEL_VERSION`: `v1`
6. Click "Create Web Service"

## Alternative: Using Render Blueprint

You can use the provided `render.yaml` file for automated deployment:

```bash
# Install Render CLI
npm install -g @renderinc/cli

# Login to Render
render login

# Deploy using blueprint
render blueprint apply render.yaml
```

## Important Notes

### Inference Service Considerations
- The inference service requires a paid plan due to TensorFlow's memory requirements
- Free tier has 512MB RAM, which is insufficient for TensorFlow models
- Starter plan provides 2GB RAM, suitable for the current model

### Database Migrations
- The API entrypoint script automatically runs migrations on startup
- Seed data is populated on first deployment
- No manual database setup required

### Environment Variables
All required environment variables are documented in the respective `.env.example` files:
- Backend: `api/.env.example`
- Frontend: `frontend/.env.example`

### Model Files
- Ensure model files are included in your Git repository
- Model location: `inference/models/v1/`
- Model size: ~28MB (within Git limits)

## Post-Deployment Steps

1. **Test the Application**
   - Access frontend: `https://agroscan-frontend.onrender.com`
   - Test image upload functionality
   - Verify API endpoints are accessible

2. **Monitor Logs**
   - Check Render dashboard for service logs
   - Monitor error rates and performance

3. **Set Up Alerts** (Optional)
   - Configure Render alerts for service failures
   - Set up uptime monitoring

## Troubleshooting

### Service Won't Start
- Check service logs in Render dashboard
- Verify environment variables are correctly set
- Ensure Dockerfiles are valid

### Database Connection Issues
- Verify DATABASE_URL format
- Check database service is running
- Ensure network connectivity between services

### Inference Service Issues
- Verify you're using Starter plan (not Free)
- Check model files are present
- Monitor memory usage in Render dashboard

### Frontend Build Failures
- Verify Node.js version compatibility
- Check package.json scripts
- Review build logs for specific errors

## Scaling Considerations

### When to Scale Up
- High traffic (>1000 requests/day)
- Slow response times
- Frequent timeouts

### Scaling Options
- **Backend**: Increase RAM/CPU or add horizontal scaling
- **Database**: Upgrade to higher tier PostgreSQL
- **Inference**: More powerful instance for faster predictions

## Cost Optimization

### Free Tier Limitations
- 512MB RAM per service
- 750 hours/month runtime
- No SSL custom domains (uses Render's SSL)

### Cost Reduction Tips
- Use free tier where possible
- Optimize model size for inference
- Implement caching to reduce API calls
- Monitor and scale down during low usage

## Security Recommendations

1. **Use Strong Secrets**
   - Generate secure JWT_SECRET
   - Rotate secrets periodically

2. **Enable HTTPS**
   - Render provides SSL by default
   - Configure custom domain if needed

3. **Database Security**
   - Use Render's internal networking
   - Don't expose database port publicly

4. **API Security**
   - Implement rate limiting (already configured)
   - Use CORS properly
   - Validate all inputs

## Monitoring and Maintenance

### Regular Tasks
- Monitor service health
- Review error logs
- Update dependencies
- Backup database (Render handles this automatically)

### Performance Monitoring
- Use Render's built-in metrics
- Set up external monitoring (optional)
- Track API response times
- Monitor inference service latency

## Support

For issues specific to:
- **Render Platform**: https://render.com/docs
- **Application Issues**: Check GitHub issues or create new one
- **Database Issues**: Render database documentation
