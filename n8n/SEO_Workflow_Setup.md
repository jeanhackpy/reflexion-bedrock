# SEO Article Monitoring & Generation Workflow

## Overview

This n8n workflow automatically monitors your Google Search Console and Google Analytics data for two WordPress websites hosted on Hostinger, then generates and publishes SEO-optimized articles based on the insights.

## Features

- **Weekly Automated Analysis**: Runs every 7 days to analyze SEO performance
- **Dual Site Support**: Monitors and generates content for two separate WordPress sites
- **AI-Powered Content Generation**: Uses your local Ollama setup for high-quality article creation
- **SEO Optimization**: Analyzes search data to identify content opportunities
- **WordPress Integration**: Automatically publishes articles as drafts to both sites
- **Email Notifications**: Sends completion notifications

## Workflow Components

### Data Collection
1. **Google Search Console**: Fetches keyword rankings, search queries, and page performance
2. **Google Analytics 4**: Retrieves traffic data, user behavior, and conversion metrics

### Analysis & Generation
3. **SEO Analysis AI**: Identifies content gaps, high-performing keywords, and trending topics
4. **Article Idea Generation**: Creates 4-6 article concepts based on data insights
5. **Content Creation**: Generates full SEO-optimized articles (1500-2500 words each)

### Publishing
6. **WordPress REST API**: Publishes articles to both Hostinger-hosted WordPress sites
7. **Email Notifications**: Sends status updates when workflow completes

## Setup Requirements

### 1. Google APIs Setup

#### Google Search Console
- Create OAuth2 credentials for each site in Google Cloud Console
- Enable Google Search Console API
- Add service account to each GSC property with "Read" permissions

#### Google Analytics 4
- Create OAuth2 credentials for each GA4 property
- Enable Google Analytics Data API
- Grant service account "Viewer" access to each GA4 property

### 2. WordPress Configuration

For each WordPress site:
- Install and activate the Yoast SEO plugin (recommended)
- Create an application password for REST API authentication
- Ensure REST API is enabled (default in WordPress)

### 3. Workflow Variables

Set these variables in your n8n instance:

```javascript
{
  // Site 1 Configuration
  "site1_url": "https://yoursite1.com",
  "ga4_property_site1": "GA4_PROPERTY_ID_1",
  "site1_wordpress_url": "https://yoursite1.hostinger.com/wp-json/wp/v2/posts",
  "site1_wp_username": "your_wp_username",
  "site1_wp_password": "your_application_password",

  // Site 2 Configuration
  "site2_url": "https://yoursite2.com",
  "ga4_property_site2": "GA4_PROPERTY_ID_2",
  "site2_wordpress_url": "https://yoursite2.hostinger.com/wp-json/wp/v2/posts",
  "site2_wp_username": "your_wp_username",
  "site2_wp_password": "your_application_password",

  // Notification
  "notification_email": "your-email@example.com"
}
```

### 4. Credentials Setup in n8n

Create these credentials in your n8n instance:

1. **Google Search Console Site 1** (OAuth2)
2. **Google Search Console Site 2** (OAuth2)
3. **Google Analytics Site 1** (OAuth2)
4. **Google Analytics Site 2** (OAuth2)
5. **SMTP Account** (for email notifications)

## Installation

1. Import the workflow JSON from `n8n/backup/workflows/SEO_Article_Monitoring_Generation.json`
2. Set up all required credentials
3. Configure workflow variables
4. Test the workflow manually first
5. Activate the schedule trigger

## Workflow Flow

```
Schedule Trigger (Weekly)
    ↓
Data Collection (GSC + GA4 for both sites)
    ↓
Data Analysis & Article Ideation
    ↓
Content Generation (AI-powered)
    ↓
Distribution to WordPress Sites
    ↓
Email Notification
```

## Customization Options

### Content Strategy
- Modify the AI prompts to match your brand voice
- Adjust article length and structure
- Add custom SEO requirements

### Publishing Rules
- Change article status (draft/publish)
- Add custom categories or tags
- Modify meta data handling

### Scheduling
- Change frequency (daily, weekly, monthly)
- Add manual triggers for on-demand generation

## Monitoring & Maintenance

- Check workflow execution logs regularly
- Review generated articles before publishing
- Monitor API rate limits for Google services
- Update credentials when they expire

## Troubleshooting

### Common Issues

1. **Google API Errors**: Verify credentials and permissions
2. **WordPress Publishing Fails**: Check REST API credentials and site URLs
3. **AI Generation Issues**: Ensure Ollama is running and accessible
4. **Email Notifications**: Verify SMTP settings

### Debug Steps

1. Run workflow manually with test data
2. Check node execution results for errors
3. Verify all credentials are properly configured
4. Test API connections individually

## Security Notes

- Store API keys and passwords securely in n8n credentials
- Use application passwords for WordPress (not main account passwords)
- Regularly rotate credentials
- Monitor for unusual API usage

## Performance Optimization

- The workflow processes data for 30 days by default
- Article generation can take 2-5 minutes per article
- Consider running during off-peak hours
- Monitor your Ollama instance resource usage