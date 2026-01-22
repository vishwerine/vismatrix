# Google AdSense Ad Placement Map

## Dashboard Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                         NAVIGATION BAR                           │
│                      (VisMatrix Header)                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        WELCOME SECTION                           │
│        "Welcome back, [username]!" + Quick Actions               │
└─────────────────────────────────────────────────────────────────┘

╔═════════════════════════════════════════════════════════════════╗
║                  📢 HEADER BANNER AD (728×90)                    ║
║                     Responsive - All Devices                     ║
╚═════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────┐
│                  Notifications (if unread)                       │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┬──────────────────────┬─────────────────────┐
│   LEFT COLUMN    │   MIDDLE COLUMN      │   RIGHT COLUMN      │
│   (Recent Logs)  │   (Friends Feed)     │   (Today's Tasks)   │
│                  │                       │                     │
│  - Recent Logs   │  - Friend Activity   │ ╔═════════════════╗ │
│  - Plans         │  - Social Posts      │ ║  📢 SIDEBAR AD  ║ │
│  - Habits        │  - Stars/Reactions   │ ║   (300×250)     ║ │
│  - Timer Session │                       │ ╚═════════════════╝ │
│                  │                       │                     │
│ ╔══════════════╗ │                       │  - Friend Requests  │
│ ║ 📢 IN-CONTENT ║ │                       │  - Today's Tasks    │
│ ║ AD (336×280) ║ │                       │  - Statistics       │
│ ╚══════════════╝ │                       │                     │
└──────────────────┴──────────────────────┴─────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      MOBILE NAVIGATION                           │
│                    (Bottom Tab Bar)                              │
└─────────────────────────────────────────────────────────────────┘
```

## Ad Placement Details

### 1. Header Banner Ad
- **Location**: After welcome section, before notifications
- **Desktop Size**: 728×90 (Leaderboard)
- **Mobile**: Responsive (adapts to screen)
- **Visibility**: HIGH - Above the fold
- **Implementation**: `{% ad_container 'header_banner' 'my-6 max-w-5xl mx-auto' %}`
- **Best For**: Maximum impressions and visibility

### 2. Sidebar Ad
- **Location**: Right column, top of sidebar
- **Size**: 300×250 (Medium Rectangle)
- **Device**: Desktop/Tablet only
- **Visibility**: MEDIUM - Persistent while scrolling
- **Implementation**: `{% ad_container 'sidebar' 'my-6' %}`
- **Best For**: Engaged desktop users

### 3. In-Content Ad
- **Location**: Bottom of left column
- **Size**: 336×280 (Large Rectangle)
- **Device**: All devices
- **Visibility**: MEDIUM-HIGH - Natural content break
- **Implementation**: `{% ad_container 'in_content' 'my-6' %}`
- **Best For**: Users scrolling through content

## Responsive Behavior

### Desktop (≥1280px - XL screens)
```
┌────────────────────────────────────────────────┐
│              Header Banner Ad                   │
│           (Full width, centered)                │
├──────────┬────────────────────┬────────────────┤
│  Left    │      Middle        │  Right + Ads   │
│  Column  │      Column        │   (Sidebar)    │
└──────────┴────────────────────┴────────────────┘
```

### Tablet (768px-1279px)
```
┌────────────────────────────────────────────────┐
│              Header Banner Ad                   │
│           (Responsive width)                    │
├──────────────────┬───────────────────────────┤
│   Left Column    │     Right Column           │
│   + In-Content   │     + Sidebar Ad           │
└──────────────────┴───────────────────────────┘
```

### Mobile (<768px)
```
┌──────────────────────────┐
│    Header Banner Ad       │
│      (Responsive)         │
├──────────────────────────┤
│    Content Stacked        │
│    (Single Column)        │
│                           │
│    In-Content Ad          │
│    (Responsive)           │
└──────────────────────────┘
```

## Ad Performance Expectations

### By Placement (Estimated CTR)

| Placement        | Expected CTR | Visibility | Revenue Potential |
|------------------|--------------|------------|-------------------|
| Header Banner    | 0.8-1.5%     | ⭐⭐⭐⭐⭐    | HIGH              |
| Sidebar          | 0.5-1.0%     | ⭐⭐⭐⭐     | MEDIUM-HIGH       |
| In-Content       | 1.0-2.0%     | ⭐⭐⭐⭐⭐    | HIGH              |

*CTR = Click-Through Rate (clicks per 100 impressions)*

## Future Expansion Opportunities

### Recommended Additional Placements

1. **Analytics Page**
   ```
   ┌─────────────────────────┐
   │   Analytics Charts       │
   ├─────────────────────────┤
   │   Sidebar Ad (300x600)   │  ← Add here
   └─────────────────────────┘
   ```

2. **Task List Page**
   ```
   ┌─────────────────────────┐
   │   Task List              │
   │   - Task 1               │
   │   - Task 2               │
   ├─────────────────────────┤
   │   In-Content Ad          │  ← Add here
   ├─────────────────────────┤
   │   - Task 3               │
   │   - Task 4               │
   └─────────────────────────┘
   ```

3. **Social Feed**
   ```
   ┌─────────────────────────┐
   │   Post 1                 │
   │   Post 2                 │
   │   Post 3                 │
   ├─────────────────────────┤
   │   Native Ad              │  ← Add here
   ├─────────────────────────┤
   │   Post 4                 │
   │   Post 5                 │
   └─────────────────────────┘
   ```

4. **Landing Page**
   ```
   ┌─────────────────────────┐
   │   Hero Section           │
   │   Features               │
   ├─────────────────────────┤
   │   Footer Banner Ad       │  ← Add here
   └─────────────────────────┘
   ```

## Mobile-Specific Considerations

### Mobile Ad Slot
- **Size**: 320×50 or 320×100
- **Recommended**: Bottom sticky banner
- **Variable**: `GOOGLE_ADS_MOBILE_SLOT`
- **Implementation**:
  ```django
  <div class="lg:hidden fixed bottom-16 left-0 right-0 z-50">
    {% google_ad 'mobile_banner' %}
  </div>
  ```

### Mobile Best Practices
✅ Use responsive ad units
✅ Avoid ads near navigation buttons
✅ Don't block content with ads
✅ Keep page load speed fast
✅ Ensure ads don't cause layout shifts

## Ad Density Guidelines

### Current Implementation
- **Dashboard Page**: 3 ads per page
- **Ad-to-Content Ratio**: ~15% (within Google's guidelines)
- **User Experience**: Balanced

### Google's Recommendations
- Maximum 3 ads per page view (currently compliant ✅)
- More content than ads (currently compliant ✅)
- Ads should not obscure content (currently compliant ✅)

### Optimization Tips
1. Start with fewer ads (current implementation is good)
2. Monitor user engagement metrics
3. Add more ads only if UX remains good
4. Test different placements
5. Remove low-performing ad units

## Visual Balance

```
GOOD BALANCE (Current Implementation):
┌──────────────────────┐
│  Content (70%)       │
│                      │
│  Ad (10%)            │
│                      │
│  Content (20%)       │
└──────────────────────┘

BAD BALANCE (Avoid This):
┌──────────────────────┐
│  Ad (30%)            │
│  Content (20%)       │
│  Ad (30%)            │
│  Content (20%)       │
└──────────────────────┘
```

## Testing Checklist

When adding new ads:
- [ ] Check mobile responsiveness
- [ ] Verify ads don't break layout
- [ ] Test page load speed
- [ ] Monitor bounce rate
- [ ] Check Core Web Vitals
- [ ] Ensure accessibility
- [ ] Test with ad blockers
- [ ] Verify console has no errors

## Color Coding Legend

📢 = Ad Placement
⭐ = Performance Rating
✅ = Compliant/Good
❌ = Non-Compliant/Bad

---

**Note**: This map shows the current implementation. Additional placements can be added based on performance data and user feedback.
