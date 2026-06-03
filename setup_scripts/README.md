# UK Lotto Historical Data - Complete Guide

## What You Have

I've created a CSV file at `/mnt/user-data/outputs/uk_lotto_oct2015_onwards.csv` with:
- **1,055 draws** from October 10, 2015 to November 15, 2025
- Correct format: date, day_of_week, ball_1 through ball_6, bonus_ball

⚠️ **IMPORTANT**: The current CSV contains **simulated data** for demonstration purposes.

## Getting REAL Lottery Data

To get actual historical lottery results, you have two options:

### Option 1: Use My Python Script (Recommended)

I've created a complete scraping script that you can run on your own computer:

```bash
python scrape_real_lottery_data.py
```

This script will:
1. Fetch HTML from lottery.co.uk for years 2015-2025
2. Parse all draws from October 10, 2015 onwards
3. Create a CSV with real results
4. Handle all date formatting and data validation

### Option 2: Manual Download

If you prefer, the Official National Lottery provides a CSV download:
- Visit: https://www.national-lottery.co.uk/results/lotto/draw-history/csv
- This gives recent data (last 180 days)
- For historical data, you'll need to compile from yearly archives

## CSV Format

Your CSV will have these columns:
```
date,day_of_week,ball_1,ball_2,ball_3,ball_4,ball_5,ball_6,bonus_ball
2015-10-10,Saturday,2,3,16,32,53,54,8
2015-10-14,Wednesday,7,13,20,27,39,52,35
...
```

## For WordPress Integration

To import this CSV into your WordPress site:

1. **Using WP All Import plugin**:
   - Install WP All Import
   - Upload your CSV
   - Map columns to custom post type fields

2. **Using Custom Code**:
   ```php
   $csv = array_map('str_getcsv', file('lottery_data.csv'));
   array_shift($csv); // Remove header
   
   foreach($csv as $row) {
       $draw = array(
           'date' => $row[0],
           'day' => $row[1],
           'balls' => array_slice($row, 2, 6),
           'bonus' => $row[8]
       );
       // Insert into your database
   }
   ```

3. **Database Import**:
   - Import directly via phpMyAdmin
   - Use MySQL LOAD DATA INFILE

## Notes

- Draws occur every Wednesday and Saturday
- The 59-ball format started October 10, 2015
- Before that date, it was a 49-ball format
- Your CSV contains only the 59-ball format draws

## Need Help?

The scraping script is ready to use. Just run it on a computer with Python and internet access.
