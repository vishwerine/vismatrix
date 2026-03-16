# User-Generated Blog Posts - Feature Documentation

## Overview

VisMatrix now allows authenticated users to write and publish their own blog posts on the platform. This feature combines static blog content (curated by the VisMatrix team) with user-generated content to create a community-driven blog platform.

## Features

### For Blog Authors

1. **Write Blog Posts**
   - Rich Markdown editor for content creation
   - Auto-generated URL slugs from titles
   - Category selection (8 categories available)
   - Draft/Published/Archived status control
   - Featured image URL support
   - SEO meta description
   - Auto-calculated read time (based on word count)

2. **Manage Your Posts**
   - View all your posts with stats (views, read time)
   - Edit published or draft posts
   - Delete posts with confirmation
   - See status badges (Draft, Published, Archived)
   - Filter by status

3. **Post Statistics**
   - View count tracking
   - Read time display
   - Publication date

### For Readers

1. **Browse All Blog Posts**
   - Static curated posts by VisMatrix Team
   - User-generated community posts
   - Category badges
   - Author attribution
   - View counts

2. **Read Blog Posts**
   - Beautiful markdown-formatted content
   - Social sharing buttons (Twitter, Facebook, LinkedIn)
   - Copy link functionality
   - Author profile section
   - Call-to-action for registration

## Available Categories

1. **Personal Development** - Growth mindset, self-improvement
2. **Productivity** - Time management, efficiency tips
3. **Habits** - Building good habits, breaking bad ones
4. **Goal Setting** - Setting and achieving goals
5. **Mental Health** - Mindfulness, stress management
6. **Career Growth** - Professional development
7. **Motivation** - Inspirational content
8. **Success Stories** - User achievements and testimonials

## Status Options

- **Draft** - Not visible to public, work in progress
- **Published** - Live on the blog, visible to all visitors
- **Archived** - Hidden from public view, retained for history

## Pages & URLs

### Public Pages (No Login Required)
- `/blog/` - Blog list page showing all published posts
- `/blog/<slug>/` - Individual blog post detail page

### Authenticated User Pages
- `/blog/new/create/` - Create new blog post
- `/blog/<slug>/edit/` - Edit your own post
- `/blog/<slug>/delete/` - Delete your own post (with confirmation)
- `/my-blog-posts/` - Dashboard showing all your posts with stats

## Markdown Formatting Guide

Users can format their blog content using Markdown syntax:

```markdown
# Heading 1
## Heading 2
### Heading 3

**bold text**
*italic text*

[link text](https://url.com)

- Bullet point
- Another point

1. Numbered list
2. Second item

> Blockquote

`inline code`

​```
code block
​```
```

## Validation Rules

### Title
- Minimum 10 characters
- Required field
- Auto-generates URL slug

### Excerpt
- Minimum 50 characters
- Maximum 300 characters
- Required field
- Shows on blog list page

### Content
- Minimum 200 characters
- Required field
- Supports Markdown formatting
- Auto-calculates read time (200 words/minute)

### Slug
- Auto-generated from title
- URL-friendly (lowercase, hyphens)
- Unique across all posts
- Cannot be manually edited

## User Permissions

### What Users Can Do:
- ✅ Create unlimited blog posts
- ✅ Edit their own posts anytime
- ✅ Delete their own posts
- ✅ View all published posts (theirs and others)
- ✅ Switch posts between draft/published/archived status

### What Users Cannot Do:
- ❌ Edit other users' posts
- ❌ Delete other users' posts
- ❌ Manually set the slug
- ❌ Modify view counts
- ❌ Change the author of a post

## Admin Features

Admins can manage all blog posts via Django Admin:

- View all blog posts from all users
- Edit any post (including slug, read time, views)
- Delete any post
- Filter by status, category, creation date
- Search by title, content, author
- View detailed statistics

Admin URL: `/admin/tracker/blogpost/`

## Integration Points

### Navigation
- Blog link in main navigation (base template)
- Blog link in landing page footer
- "Write a Post" button (authenticated users only)
- "My Posts" button (authenticated users only)

### Analytics & Monetization
- All blog pages track visitor analytics
- Google AdSense integration on all blog pages
- View count tracking per post

### Social Features
- Author attribution with username
- Social share buttons on each post
- Author profile section

## Database Model

The `BlogPost` model includes:

```python
- author (ForeignKey to User)
- title (CharField, max 200)
- slug (SlugField, unique, auto-generated)
- excerpt (CharField, max 300)
- content (TextField, Markdown format)
- category (8 choices)
- status (draft/published/archived)
- featured_image (URLField, optional)
- meta_description (TextField, optional)
- read_time (IntegerField, auto-calculated)
- views (IntegerField, default 0)
- published_at (DateTimeField, auto-set on publish)
- created_at (DateTimeField, auto)
- updated_at (DateTimeField, auto)
```

## SEO Features

1. **Auto-generated slugs** - Clean, URL-friendly permalinks
2. **Meta descriptions** - Optional custom SEO descriptions
3. **Read time calculation** - Improves engagement metrics
4. **View counting** - Tracks popularity
5. **Published dates** - Helps with content freshness
6. **Category organization** - Improves content discoverability

## Technical Implementation

### Files Created/Modified

1. **Models** - `tracker/models.py`
   - Added `BlogPost` model with comprehensive fields

2. **Forms** - `tracker/forms.py`
   - Added `BlogPostForm` with validation and DaisyUI styling

3. **Views** - `tracker/views.py`
   - Updated `blog_list()` - combines static + user posts
   - Updated `blog_detail()` - handles both post types
   - Added `blog_create()` - create new posts
   - Added `blog_edit()` - edit own posts
   - Added `blog_delete()` - delete own posts
   - Added `blog_my_posts()` - dashboard for user's posts

4. **URLs** - `tracker/urls.py`
   - Added blog management URL patterns

5. **Templates**
   - `blog_form.html` - Create/edit form with live counters
   - `blog_my_posts.html` - User's posts dashboard
   - `blog_confirm_delete.html` - Delete confirmation page
   - `blog_detail_user.html` - Display user-generated posts
   - Updated `blog_list.html` - Added "Write a Post" button

6. **Admin** - `tracker/admin.py`
   - Registered `BlogPost` model with comprehensive admin interface

7. **Migration**
   - `tracker/migrations/0026_blogpost.py`

## Dependencies

- Django 5.2.8
- Markdown (already in requirements.txt)
- DaisyUI (for form styling)
- Bootstrap Icons (for UI icons)

## Usage Examples

### Creating a Blog Post

1. Navigate to Blog page
2. Click "Write a Post" (must be logged in)
3. Fill in:
   - Title (minimum 10 chars)
   - Category selection
   - Excerpt (50-300 chars)
   - Content in Markdown (minimum 200 chars)
   - Optional: Featured image URL
   - Optional: SEO meta description
   - Status: Draft or Published
4. Click "Create Post"
5. Redirected to "My Posts" dashboard

### Managing Your Posts

1. Click "My Posts" in navigation
2. See all your posts with stats:
   - Published count
   - Draft count
   - Total views across all posts
3. Actions available:
   - Edit - Modify any post
   - Delete - Remove permanently
   - View - See published post live

### Publishing a Draft

1. Go to "My Posts"
2. Click "Edit" on a draft post
3. Change Status from "Draft" to "Published"
4. Click "Update Post"
5. Post is now live and visible to all

## Future Enhancements

Potential features for future development:

- Comments system on blog posts
- Like/reaction buttons
- Post tagging system
- Search functionality
- RSS feed generation
- Email notifications for new posts
- Featured posts section
- Related posts recommendations
- File upload for images (instead of URLs)
- Rich text editor option (WYSIWYG)
- Post preview before publishing
- Scheduled publishing
- Co-author support
- Post series/collections

## Support

For questions or issues with the blog functionality:
1. Check this documentation
2. Contact VisMatrix support
3. Report bugs via the admin panel

---

**Last Updated:** January 2026  
**Version:** 1.0  
**Author:** VisMatrix Development Team
