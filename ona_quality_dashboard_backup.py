
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from datetime import datetime, timedelta
import numpy as np
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ONAQualityDashboard:
    def __init__(self, data_file, config=None):
        """Initialize dashboard with data file and optional config"""
        self.data_file = data_file
        self.config = config or {}
        self.df = None
        self.district_col = None
        self.target_districts = ['Bosaso', 'Dhusamareb', 'Beletweyne', 'Baki', 'Gabiley']
        
        # Target configurations
        self.district_targets = self.config.get('district_targets', {
            'Bosaso': 100,
            'Dhusamareb': 100,
            'Beletweyne': 100,
            'Baki': 50,
            'Gabiley': 50
        })
        
        self.beneficiary_ratio = self.config.get('beneficiary_ratio', 0.5)  # 50% beneficiaries target
        
    def load_data(self):
        """Load data from CSV file"""
        try:
            self.df = pd.read_csv(self.data_file)
            logger.info(f"Loaded {len(self.df)} records from {self.data_file}")
            
            # Convert date columns
            date_columns = ['start', 'end', 'today', '_submission_time']
            for col in date_columns:
                if col in self.df.columns:
                    self.df[col] = pd.to_datetime(self.df[col])
                    
            return True
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False
    
    def _find_column(self, column_name, keywords):
        """Find a column by searching for keywords in column names"""
        if column_name and column_name in self.df.columns:
            return column_name
        
        for col in self.df.columns:
            col_lower = col.lower()
            if any(keyword.lower() in col_lower for keyword in keywords):
                logger.info(f"Found column '{col}' for {keywords}")
                return col
        
        return None
    
    def _create_empty_pivot(self):
        """Create empty pivot table structure"""
        empty_data = {
            'District': self.target_districts + ['Total'],
            'Beneficiary': [0] * (len(self.target_districts) + 1),
            'Non-Beneficiary': [0] * (len(self.target_districts) + 1),
            'Total': [0] * (len(self.target_districts) + 1)
        }
        return empty_data
    
    def _detect_duplicates(self):
        """Detect potential duplicate surveys"""
        if self.df is None:
            return []
        
        duplicates = []
        
        # Check for duplicate GPS coordinates (within 10 meters)
        if 'latitude' in self.df.columns and 'longitude' in self.df.columns:
            gps_df = self.df[['latitude', 'longitude']].dropna()
            gps_rounded = gps_df.round(4)  # ~10m precision
            dup_gps = gps_rounded[gps_rounded.duplicated(keep=False)]
            if len(dup_gps) > 0:
                duplicates.append(f"{len(dup_gps)} surveys with duplicate GPS")
        
        # Check for same enumerator, same day, similar duration
        if '_submission_time' in self.df.columns and 'duration_minutes' in self.df.columns:
            self.df['submission_date'] = self.df['_submission_time'].dt.date
            
        return duplicates
    
    def _calculate_progress_tracker(self, district_col):
        """Calculate collection progress vs targets"""
        if not district_col or district_col not in self.df.columns:
            return None
        
        progress = {
            'District': [],
            'Target': [],
            'Actual': [],
            'Remaining': [],
            'Progress %': [],
            'Status': []
        }
        
        actual_counts = self.df[district_col].value_counts().to_dict()
        
        for district in self.target_districts:
            target = self.district_targets.get(district, 100)
            actual = actual_counts.get(district, 0)
            remaining = max(0, target - actual)
            progress_pct = min(100, (actual / target * 100) if target > 0 else 0)
            
            if progress_pct >= 100:
                status = '✅ Complete'
            elif progress_pct >= 75:
                status = '🟡 On Track'
            elif progress_pct >= 50:
                status = '🟠 Behind'
            else:
                status = '🔴 Critical'
            
            progress['District'].append(district)
            progress['Target'].append(target)
            progress['Actual'].append(actual)
            progress['Remaining'].append(remaining)
            progress['Progress %'].append(f"{progress_pct:.1f}%")
            progress['Status'].append(status)
        
        # Add totals
        total_target = sum(self.district_targets.values())
        total_actual = sum(actual_counts.get(d, 0) for d in self.target_districts)
        total_remaining = max(0, total_target - total_actual)
        total_progress = min(100, (total_actual / total_target * 100) if total_target > 0 else 0)
        
        progress['District'].append('TOTAL')
        progress['Target'].append(total_target)
        progress['Actual'].append(total_actual)
        progress['Remaining'].append(total_remaining)
        progress['Progress %'].append(f"{total_progress:.1f}%")
        progress['Status'].append('🎯 Overall')
        
        return progress
    
    def _generate_alerts(self, enum_col, duration_col, district_col):
        """Generate real-time alerts for issues needing attention"""
        alerts = []
        
        # Check for today's invalid surveys
        if '_submission_time' in self.df.columns and 'is_valid' in self.df.columns:
            today = datetime.now().date()
            today_data = self.df[self.df['_submission_time'].dt.date == today]
            invalid_today = (~today_data['is_valid']).sum()
            if invalid_today > 0:
                alerts.append(f"⚠️ {invalid_today} invalid surveys submitted TODAY")
        
        # Check for enumerators with high invalid rate
        if enum_col and enum_col in self.df.columns and 'is_valid' in self.df.columns:
            enum_stats = self.df.groupby(enum_col).agg({
                'is_valid': ['sum', 'count']
            })
            enum_stats.columns = ['valid', 'total']
            enum_stats['invalid_rate'] = (1 - enum_stats['valid'] / enum_stats['total']) * 100
            
            problem_enums = enum_stats[enum_stats['invalid_rate'] > 50]
            for enum_name, row in problem_enums.iterrows():
                alerts.append(f"🚨 Enumerator '{enum_name}' has {row['invalid_rate']:.0f}% invalid rate")
        
        # Check for districts with no recent submissions
        if '_submission_time' in self.df.columns and district_col and district_col in self.df.columns:
            last_24h = datetime.now() - timedelta(hours=24)
            recent_data = self.df[self.df['_submission_time'] >= last_24h]
            recent_districts = set(recent_data[district_col].unique())
            
            for district in self.target_districts:
                if district not in recent_districts:
                    alerts.append(f"📍 No submissions from {district} in last 24 hours")
        
        # Check for missing GPS
        if 'latitude' in self.df.columns and 'longitude' in self.df.columns:
            missing_gps = self.df[['latitude', 'longitude']].isna().any(axis=1).sum()
            if missing_gps > 0:
                alerts.append(f"📍 {missing_gps} surveys missing GPS coordinates")
        
        # Check for duplicates
        duplicates = self._detect_duplicates()
        alerts.extend(duplicates)
        
        # Check progress for districts far behind
        if district_col and district_col in self.df.columns:
            actual_counts = self.df[district_col].value_counts().to_dict()
            for district in self.target_districts:
                target = self.district_targets.get(district, 100)
                actual = actual_counts.get(district, 0)
                progress_pct = (actual / target * 100) if target > 0 else 0
                
                if progress_pct < 25 and target > 0:
                    remaining = target - actual
                    alerts.append(f"🔴 {district}: Only {actual}/{target} surveys ({progress_pct:.0f}%) - Need {remaining} more")
        
        return alerts[:10]  # Return top 10 alerts
    
    def _calculate_daily_summary(self):
        """Calculate today, yesterday, and this week statistics"""
        if '_submission_time' not in self.df.columns:
            return None
        
        now = datetime.now()
        today = now.date()
        yesterday = today - timedelta(days=1)
        week_start = today - timedelta(days=7)
        
        today_data = self.df[self.df['_submission_time'].dt.date == today]
        yesterday_data = self.df[self.df['_submission_time'].dt.date == yesterday]
        week_data = self.df[self.df['_submission_time'].dt.date >= week_start]
        
        summary = {
            'Period': ['TODAY', 'YESTERDAY', 'THIS WEEK'],
            'Surveys': [
                len(today_data),
                len(yesterday_data),
                len(week_data)
            ],
            'Valid %': [
                f"{(today_data['is_valid'].sum() / len(today_data) * 100):.0f}%" if len(today_data) > 0 and 'is_valid' in today_data.columns else 'N/A',
                f"{(yesterday_data['is_valid'].sum() / len(yesterday_data) * 100):.0f}%" if len(yesterday_data) > 0 and 'is_valid' in yesterday_data.columns else 'N/A',
                f"{(week_data['is_valid'].sum() / len(week_data) * 100):.0f}%" if len(week_data) > 0 and 'is_valid' in week_data.columns else 'N/A'
            ],
            'Avg Duration': [
                f"{today_data['duration_minutes'].mean():.0f}min" if len(today_data) > 0 and 'duration_minutes' in today_data.columns else 'N/A',
                f"{yesterday_data['duration_minutes'].mean():.0f}min" if len(yesterday_data) > 0 and 'duration_minutes' in yesterday_data.columns else 'N/A',
                f"{week_data['duration_minutes'].mean():.0f}min" if len(week_data) > 0 and 'duration_minutes' in week_data.columns else 'N/A'
            ]
        }
        
        return summary
    
    def _calculate_enumerator_leaderboard(self, enum_col, duration_col):
        """Calculate enumerator performance leaderboard"""
        if not enum_col or enum_col not in self.df.columns:
            return None, None
        
        enum_stats = []
        
        for enum in self.df[enum_col].unique():
            enum_data = self.df[self.df[enum_col] == enum]
            
            total = len(enum_data)
            valid = enum_data['is_valid'].sum() if 'is_valid' in enum_data.columns else total
            valid_pct = (valid / total * 100) if total > 0 else 0
            avg_duration = enum_data[duration_col].mean() if duration_col in enum_data.columns else 0
            
            enum_stats.append({
                'enumerator': str(enum),
                'total': total,
                'valid': valid,
                'valid_pct': valid_pct,
                'avg_duration': avg_duration,
                'score': valid_pct * 0.7 + min(100, (total / 10) * 10) * 0.3  # Composite score
            })
        
        # Sort by score
        enum_stats.sort(key=lambda x: x['score'], reverse=True)
        
        # Top performers (top 5)
        top_performers = {
            'Rank': [],
            'Enumerator': [],
            'Surveys': [],
            'Valid %': [],
            'Avg Duration': []
        }
        
        for i, stats in enumerate(enum_stats[:5], 1):
            top_performers['Rank'].append(f"🏆 {i}")
            top_performers['Enumerator'].append(stats['enumerator'])
            top_performers['Surveys'].append(stats['total'])
            top_performers['Valid %'].append(f"{stats['valid_pct']:.0f}%")
            top_performers['Avg Duration'].append(f"{stats['avg_duration']:.0f}min")
        
        # Need support (bottom 5 with >5 surveys)
        bottom_performers = [s for s in enum_stats if s['total'] >= 5]
        bottom_performers.sort(key=lambda x: x['valid_pct'])
        
        needs_support = {
            'Rank': [],
            'Enumerator': [],
            'Surveys': [],
            'Valid %': [],
            'Issues': []
        }
        
        for i, stats in enumerate(bottom_performers[:5], 1):
            needs_support['Rank'].append(f"⚠️ {i}")
            needs_support['Enumerator'].append(stats['enumerator'])
            needs_support['Surveys'].append(stats['total'])
            needs_support['Valid %'].append(f"{stats['valid_pct']:.0f}%")
            
            issues = []
            if stats['valid_pct'] < 70:
                issues.append('Low validity')
            if stats['avg_duration'] < 50:
                issues.append('Too fast')
            if stats['avg_duration'] > 120:
                issues.append('Too slow')
            
            needs_support['Issues'].append(', '.join(issues) if issues else 'Review needed')
        
        return top_performers, needs_support
    
    def _calculate_quality_dimensions(self, duration_col):
        """Calculate multi-dimensional quality scores"""
        dimensions = {}
        
        # Completeness
        completeness = (1 - self.df.isnull().sum().sum() / (len(self.df) * len(self.df.columns))) * 100
        dimensions['Completeness'] = completeness
        
        # Duration Validity
        if 'is_valid' in self.df.columns:
            duration_validity = (self.df['is_valid'].sum() / len(self.df)) * 100
            dimensions['Duration Validity'] = duration_validity
        
        # GPS Accuracy
        if 'latitude' in self.df.columns and 'longitude' in self.df.columns:
            gps_accuracy = (self.df[['latitude', 'longitude']].notna().all(axis=1).sum() / len(self.df)) * 100
            dimensions['GPS Accuracy'] = gps_accuracy
        
        # Logical Consistency (no extreme outliers in key fields)
        consistency_score = 100  # Start at 100
        if duration_col in self.df.columns:
            extreme_durations = ((self.df[duration_col] < 10) | (self.df[duration_col] > 300)).sum()
            consistency_score -= (extreme_durations / len(self.df)) * 100
        
        dimensions['Logical Consistency'] = max(0, consistency_score)
        
        # Duplicate Detection
        duplicates = len(self._detect_duplicates())
        duplicate_score = max(0, 100 - (duplicates * 10))
        dimensions['Duplicate Check'] = duplicate_score
        
        return dimensions
    
    def _calculate_beneficiary_balance(self, district_col):
        """Calculate beneficiary balance scorecard"""
        treatment_col = 'respondent_information/treatment'
        
        if treatment_col not in self.df.columns or not district_col or district_col not in self.df.columns:
            return None
        
        balance = {
            'District': [],
            'Beneficiaries': [],
            'Non-Beneficiaries': [],
            'Ratio': [],
            'Target Ratio': [],
            'Status': []
        }
        
        for district in self.target_districts:
            district_data = self.df[self.df[district_col] == district]
            
            beneficiaries = (district_data[treatment_col] == 'Beneficiary').sum()
            non_beneficiaries = (district_data[treatment_col] == 'NotBeneficiary').sum()
            total = beneficiaries + non_beneficiaries
            
            if total > 0:
                ratio = beneficiaries / total
                target = self.beneficiary_ratio
                diff = abs(ratio - target)
                
                if diff < 0.05:
                    status = '✅ Balanced'
                elif diff < 0.15:
                    status = '🟡 Acceptable'
                else:
                    status = '🔴 Unbalanced'
            else:
                ratio = 0
                status = '⚪ No Data'
            
            balance['District'].append(district)
            balance['Beneficiaries'].append(beneficiaries)
            balance['Non-Beneficiaries'].append(non_beneficiaries)
            balance['Ratio'].append(f"{ratio:.1%}")
            balance['Target Ratio'].append(f"{self.beneficiary_ratio:.1%}")
            balance['Status'].append(status)
        
        return balance
    
    def _calculate_time_analysis(self):
        """Analyze interview patterns by time"""
        if '_submission_time' not in self.df.columns:
            return None, None
        
        # Peak hours analysis
        self.df['hour'] = self.df['_submission_time'].dt.hour
        hourly_counts = self.df['hour'].value_counts().sort_index()
        
        # Weekend vs weekday
        self.df['is_weekend'] = self.df['_submission_time'].dt.dayofweek >= 5
        weekend_data = self.df[self.df['is_weekend']]
        weekday_data = self.df[~self.df['is_weekend']]
        
        time_stats = {
            'Metric': ['Weekday Surveys', 'Weekend Surveys', 'Peak Hour', 'Avg Weekday Duration', 'Avg Weekend Duration'],
            'Value': [
                len(weekday_data),
                len(weekend_data),
                f"{hourly_counts.idxmax()}:00" if len(hourly_counts) > 0 else 'N/A',
                f"{weekday_data['duration_minutes'].mean():.0f}min" if 'duration_minutes' in weekday_data.columns and len(weekday_data) > 0 else 'N/A',
                f"{weekend_data['duration_minutes'].mean():.0f}min" if 'duration_minutes' in weekend_data.columns and len(weekend_data) > 0 else 'N/A'
            ]
        }
        
        return hourly_counts, time_stats
    
    def _create_beneficiary_pivot_table(self):
        """Create beneficiary vs non-beneficiary comparison table"""
        try:
            treatment_col = 'respondent_information/treatment'
            
            if treatment_col not in self.df.columns:
                print(f"\n✗ Treatment column '{treatment_col}' not found!")
                return self._create_empty_pivot()
            
            print(f"\n✓ Found treatment column: {treatment_col}")
            
            analysis_df = self.df[[self.district_col, treatment_col]].copy()
            
            def categorize_treatment(val):
                if pd.isna(val):
                    return 'Unknown'
                val_str = str(val).strip()
                if val_str == 'Beneficiary':
                    return 'Beneficiary'
                elif val_str == 'NotBeneficiary':
                    return 'Non-Beneficiary'
                else:
                    return 'Unknown'
            
            analysis_df['Beneficiary_Status'] = analysis_df[treatment_col].apply(categorize_treatment)
            
            pivot = pd.crosstab(
                analysis_df[self.district_col],
                analysis_df['Beneficiary_Status'],
                margins=True,
                margins_name='Total'
            )
            
            for district in self.target_districts:
                if district not in pivot.index:
                    pivot.loc[district] = 0
            
            for status in ['Beneficiary', 'Non-Beneficiary']:
                if status not in pivot.columns:
                    pivot[status] = 0
            
            cols_order = [col for col in ['Beneficiary', 'Non-Beneficiary', 'Unknown', 'Total'] 
                         if col in pivot.columns]
            pivot = pivot[cols_order]
            
            district_order = [d for d in self.target_districts if d in pivot.index]
            if 'Total' in pivot.index:
                district_order.append('Total')
            pivot = pivot.loc[district_order]
            
            result = {'District': list(pivot.index)}
            for col in pivot.columns:
                result[col] = list(pivot[col].values)
            
            return result
            
        except Exception as e:
            print(f"\n✗ Error creating beneficiary pivot: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_empty_pivot()
    
    def generate_dashboard(self, output_file='ona_dashboard_enhanced.html', 
                          title='ONA Data Quality Dashboard - Enhanced',
                          district_column='district',
                          duration_column='duration_minutes',
                          enumerator_column=None,
                          lat_column='latitude',
                          lon_column='longitude'):
        """Generate comprehensive interactive HTML dashboard with all features"""
        
        if self.df is None or len(self.df) == 0:
            logger.error("No data available to generate dashboard")
            return False
        
        try:
            # Smart column detection
            district_column = self._find_column(district_column, ['district', 'District_id'])
            self.district_col = district_column
            enumerator_column = self._find_column(enumerator_column, ['enum', 'enumerator', 'interviewer'])
            
            min_duration_threshold = 50
            max_duration_threshold = self.config.get('max_duration', 120)
            
            logger.info(f"Generating enhanced dashboard with all features...")
            
            # Mark invalid interviews
            if duration_column in self.df.columns:
                self.df['is_valid'] = self.df[duration_column] >= min_duration_threshold
                self.df['is_too_long'] = self.df[duration_column] > max_duration_threshold
                self.df['is_too_short'] = self.df[duration_column] < min_duration_threshold
            
            # Calculate all metrics
            progress_data = self._calculate_progress_tracker(district_column)
            alerts = self._generate_alerts(enumerator_column, duration_column, district_column)
            daily_summary = self._calculate_daily_summary()
            top_performers, needs_support = self._calculate_enumerator_leaderboard(enumerator_column, duration_column)
            quality_dimensions = self._calculate_quality_dimensions(duration_column)
            beneficiary_balance = self._calculate_beneficiary_balance(district_column)
            hourly_counts, time_stats = self._calculate_time_analysis()
            
            # Create figure with 10 rows for all visualizations
            fig = make_subplots(
                rows=10, cols=3,
                subplot_titles=(
                    '🎯 Collection Progress by District',
                    '🚨 Real-Time Alerts',
                    '📊 Daily Summary',
                    '⭐ Quality Score Breakdown',
                    '📈 Progress vs Target',
                    '🏆 Top Performers',
                    '📊 Surveys by District',
                    '⏱️ Interview Duration',
                    '👥 Submissions by Enumerator',
                    '📍 Interview Locations Map',
                    '📈 Daily Submission Trends',
                    '⚠️ Validity Status',
                    '🕐 Peak Interview Hours',
                    '📅 Time Analysis',
                    '⚖️ Beneficiary Balance',
                    '👥 Beneficiary by District',
                    '🔍 Missing Data Patterns',
                    '⚠️ Needs Support',
                    '📋 Completion Stats',
                    '🎯 Overall Quality',
                    '⚠️ Enumerator Performance Details',
                    '',
                    ''
                ),
                specs=[
                    [{"type": "table", "colspan": 2}, None, {"type": "table"}],
                    [{"type": "indicator", "colspan": 3}, None, None],
                    [{"type": "bar", "colspan": 2}, None, {"type": "table"}],
                    [{"type": "bar"}, {"type": "box"}, {"type": "bar"}],
                    [{"type": "scattermapbox", "colspan": 2}, None, {"type": "bar"}],
                    [{"type": "scatter", "colspan": 2}, None, {"type": "bar"}],
                    [{"type": "bar"}, {"type": "table"}, {"type": "table"}],
                    [{"type": "table", "colspan": 2}, None, {"type": "table"}],
                    [{"type": "table", "colspan": 2}, None, {"type": "indicator"}],
                    [{"type": "table", "colspan": 3}, None, None]
                ],
                row_heights=[0.10, 0.08, 0.10, 0.12, 0.15, 0.12, 0.10, 0.10, 0.08, 0.10],
                vertical_spacing=0.04,
                horizontal_spacing=0.10
            )
            
            # Color palette
            colors = {
                'primary': '#667eea',
                'success': '#4caf50',
                'warning': '#ff9800',
                'danger': '#f44336',
                'info': '#4facfe'
            }
            
            # 1. PROGRESS TRACKER TABLE
            if progress_data:
                fig.add_trace(
                    go.Table(
                        header=dict(
                            values=list(progress_data.keys()),
                            fill_color=colors['primary'],
                            font=dict(color='white', size=12, family='Arial Black'),
                            align='center',
                            height=30
                        ),
                        cells=dict(
                            values=list(progress_data.values()),
                            fill_color=[['#f0f4f8', '#ffffff'] * (len(progress_data['District']) // 2)],
                            font=dict(color='#333', size=11),
                            align='center',
                            height=28
                        )
                    ),
                    row=1, col=1
                )
            
            # 2. ALERTS PANEL
            if alerts:
                alerts_html = '<br>'.join([f"<b>{i+1}.</b> {alert}" for i, alert in enumerate(alerts)])
                fig.add_trace(
                    go.Table(
                        header=dict(
                            values=['<b>🚨 IMMEDIATE ATTENTION NEEDED</b>'],
                            fill_color=colors['danger'],
                            font=dict(color='white', size=12, family='Arial Black'),
                            align='left',
                            height=30
                        ),
                        cells=dict(
                            values=[alerts],
                            fill_color='#fff3f3',
                            font=dict(color='#333', size=10),
                            align='left',
                            height=25
                        )
                    ),
                    row=1, col=3
                )
            
            # 3. DAILY SUMMARY
            if daily_summary:
                fig.add_trace(
                    go.Table(
                        header=dict(
                            values=list(daily_summary.keys()),
                            fill_color=colors['info'],
                            font=dict(color='white', size=12, family='Arial Black'),
                            align='center',
                            height=30
                        ),
                        cells=dict(
                            values=list(daily_summary.values()),
                            fill_color=[['#e3f2fd', '#ffffff', '#e3f2fd']],
                            font=dict(color='#333', size=13, family='Arial Black'),
                            align='center',
                            height=35
                        )
                    ),
                    row=1, col=3
                )
            
            # 4. QUALITY DIMENSIONS (Multi-indicator)
            if quality_dimensions:
                dim_text = '<br>'.join([f"<b>{k}:</b> {v:.0f}%" for k, v in quality_dimensions.items()])
                
                for i, (dim, score) in enumerate(quality_dimensions.items()):
                    color = colors['success'] if score >= 80 else colors['warning'] if score >= 60 else colors['danger']
                    
                    fig.add_trace(
                        go.Indicator(
                            mode="gauge+number",
                            value=score,
                            title={'text': f"<b>{dim}</b>", 'font': {'size': 10}},
                            gauge={
                                'axis': {'range': [0, 100]},
                                'bar': {'color': color, 'thickness': 0.7},
                                'steps': [
                                    {'range': [0, 60], 'color': '#ffebee'},
                                    {'range': [60, 80], 'color': '#fff9c4'},
                                    {'range': [80, 100], 'color': '#e8f5e9'}
                                ]
                            },
                            domain={'row': 1, 'column': i}
                        ),
                        row=2, col=1
                    )
            
            # 5. PROGRESS VS TARGET (Bar Chart)
            if progress_data:
                districts = [d for d in progress_data['District'] if d != 'TOTAL']
                targets = [progress_data['Target'][i] for i, d in enumerate(progress_data['District']) if d != 'TOTAL']
                actuals = [progress_data['Actual'][i] for i, d in enumerate(progress_data['District']) if d != 'TOTAL']
                
                fig.add_trace(
                    go.Bar(
                        name='Target',
                        x=districts,
                        y=targets,
                        marker_color=colors['info'],
                        text=targets,
                        textposition='outside'
                    ),
                    row=3, col=1
                )
                
                fig.add_trace(
                    go.Bar(
                        name='Actual',
                        x=districts,
                        y=actuals,
                        marker_color=colors['success'],
                        text=actuals,
                        textposition='outside'
                    ),
                    row=3, col=1
                )
            
            # 6. TOP PERFORMERS
            if top_performers:
                fig.add_trace(
                    go.Table(
                        header=dict(
                            values=list(top_performers.keys()),
                            fill_color='#4caf50',
                            font=dict(color='white', size=11, family='Arial Black'),
                            align='center',
                            height=30
                        ),
                        cells=dict(
                            values=list(top_performers.values()),
                            fill_color='#e8f5e9',
                            font=dict(color='#333', size=10),
                            align='center',
                            height=28
                        )
                    ),
                    row=3, col=3
                )
            
            # 7-9. STANDARD CHARTS (Surveys, Duration, Enumerators)
            if district_column and district_column in self.df.columns:
                district_data = self.df[district_column].value_counts().sort_values(ascending=True)
                fig.add_trace(
                    go.Bar(
                        y=district_data.index,
                        x=district_data.values,
                        orientation='h',
                        marker_color=colors['primary'],
                        text=district_data.values,
                        textposition='outside'
                    ),
                    row=4, col=1
                )
            
            if duration_column in self.df.columns:
                fig.add_trace(
                    go.Box(
                        y=self.df[duration_column],
                        marker_color=colors['primary'],
                        name='Duration'
                    ),
                    row=4, col=2
                )
                fig.add_hline(y=min_duration_threshold, line_dash="solid", line_color="red", line_width=2, row=4, col=2)
            
            if enumerator_column and enumerator_column in self.df.columns:
                enum_data = self.df[enumerator_column].value_counts().head(10)
                fig.add_trace(
                    go.Bar(
                        x=enum_data.index,
                        y=enum_data.values,
                        marker_color=colors['info'],
                        text=enum_data.values,
                        textposition='outside'
                    ),
                    row=4, col=3
                )
            
            # 10. GPS MAP
            if lat_column in self.df.columns and lon_column in self.df.columns:
                valid_gps = self.df.dropna(subset=[lat_column, lon_column])
                if len(valid_gps) > 0:
                    fig.add_trace(
                        go.Scattermapbox(
                            lat=valid_gps[lat_column],
                            lon=valid_gps[lon_column],
                            mode='markers',
                            marker=dict(size=8, color='#ff6b6b', opacity=0.7),
                            name='Interviews'
                        ),
                        row=5, col=1
                    )
            
            # 11. DAILY TRENDS
            if '_submission_time' in self.df.columns:
                daily_data = self.df.groupby(self.df['_submission_time'].dt.date).size()
                fig.add_trace(
                    go.Scatter(
                        x=daily_data.index,
                        y=daily_data.values,
                        mode='lines+markers',
                        line=dict(color=colors['primary'], width=2),
                        fill='tozeroy'
                    ),
                    row=6, col=1
                )
            
            # 12. VALIDITY STATUS
            if 'is_valid' in self.df.columns:
                valid = self.df['is_valid'].sum()
                invalid = (~self.df['is_valid']).sum()
                too_long = self.df['is_too_long'].sum()
                
                fig.add_trace(
                    go.Bar(
                        x=['✅ Valid', '❌ Invalid', '⚠️ Too Long'],
                        y=[valid, invalid, too_long],
                        marker=dict(color=[colors['success'], colors['danger'], colors['warning']]),
                        text=[valid, invalid, too_long],
                        textposition='outside'
                    ),
                    row=6, col=3
                )
            
            # 13. PEAK HOURS
            if hourly_counts is not None:
                fig.add_trace(
                    go.Bar(
                        x=hourly_counts.index,
                        y=hourly_counts.values,
                        marker_color=colors['info'],
                        text=hourly_counts.values,
                        textposition='outside'
                    ),
                    row=7, col=1
                )
            
            # 14. TIME ANALYSIS
            if time_stats:
                fig.add_trace(
                    go.Table(
                        header=dict(
                            values=list(time_stats.keys()),
                            fill_color=colors['primary'],
                            font=dict(color='white', size=11, family='Arial Black'),
                            align='center'
                        ),
                        cells=dict(
                            values=list(time_stats.values()),
                            fill_color='#f0f4f8',
                            font=dict(color='#333', size=10),
                            align='center'
                        )
                    ),
                    row=7, col=2
                )
            
            # 15. BENEFICIARY BALANCE
            if beneficiary_balance:
                fig.add_trace(
                    go.Table(
                        header=dict(
                            values=list(beneficiary_balance.keys()),
                            fill_color=colors['primary'],
                            font=dict(color='white', size=11, family='Arial Black'),
                            align='center'
                        ),
                        cells=dict(
                            values=list(beneficiary_balance.values()),
                            fill_color='#f0f4f8',
                            font=dict(color='#333', size=10),
                            align='center'
                        )
                    ),
                    row=7, col=3
                )
            
            # 16. BENEFICIARY PIVOT
            beneficiary_pivot = self._create_beneficiary_pivot_table()
            fig.add_trace(
                go.Table(
                    header=dict(
                        values=list(beneficiary_pivot.keys()),
                        fill_color=colors['info'],
                        font=dict(color='white', size=12, family='Arial Black'),
                        align='center'
                    ),
                    cells=dict(
                        values=list(beneficiary_pivot.values()),
                        fill_color='#f0f4f8',
                        font=dict(color='#333', size=11),
                        align='center'
                    )
                ),
                row=8, col=1
            )
            
            # 17. MISSING DATA
            missing_data = (self.df.isnull().sum() / len(self.df) * 100).sort_values(ascending=False).head(8)
            missing_data = missing_data[missing_data > 0]
            
            if len(missing_data) > 0:
                display_names = [col.split('/')[-1] if '/' in col else col for col in missing_data.index]
                fig.add_trace(
                    go.Bar(
                        y=display_names,
                        x=missing_data.values,
                        orientation='h',
                        marker_color=colors['danger'],
                        text=[f'{v:.1f}%' for v in missing_data.values],
                        textposition='outside'
                    ),
                    row=8, col=3
                )
            
            # 18. NEEDS SUPPORT
            if needs_support:
                fig.add_trace(
                    go.Table(
                        header=dict(
                            values=list(needs_support.keys()),
                            fill_color=colors['warning'],
                            font=dict(color='white', size=11, family='Arial Black'),
                            align='center'
                        ),
                        cells=dict(
                            values=list(needs_support.values()),
                            fill_color='#fff9c4',
                            font=dict(color='#333', size=10),
                            align='center'
                        )
                    ),
                    row=8, col=3
                )
            
            # 19. COMPLETION STATS
            completion_data = self._calculate_completion_stats(district_column, duration_column, enumerator_column)
            fig.add_trace(
                go.Table(
                    header=dict(
                        values=['<b>Metric</b>', '<b>Value</b>'],
                        fill_color=colors['primary'],
                        font=dict(color='white', size=12, family='Arial Black'),
                        align='left'
                    ),
                    cells=dict(
                        values=[
                            list(completion_data.keys()),
                            list(completion_data.values())
                        ],
                        fill_color=[['#f0f4f8', '#ffffff'] * len(completion_data)],
                        font=dict(color='#333', size=11),
                        align='left'
                    )
                ),
                row=9, col=1
            )
            
            # 20. OVERALL QUALITY GAUGE
            quality_score = self._calculate_quality_score(duration_column, min_duration_threshold)
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=quality_score,
                    title={'text': "<b>Overall Quality</b>", 'font': {'size': 18}},
                    delta={'reference': 85},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': colors['primary'], 'thickness': 0.75},
                        'steps': [
                            {'range': [0, 50], 'color': '#ffebee'},
                            {'range': [50, 75], 'color': '#fff9c4'},
                            {'range': [75, 100], 'color': '#e8f5e9'}
                        ],
                        'threshold': {'line': {'color': "red", 'width': 4}, 'value': 90}
                    }
                ),
                row=9, col=3
            )
            
            # 21. DETAILED ENUMERATOR PERFORMANCE
            if enumerator_column and enumerator_column in self.df.columns:
                enum_performance = self._calculate_enumerator_performance_detailed(
                    enumerator_column, duration_column, district_column,
                    lat_column, lon_column, min_duration_threshold, max_duration_threshold
                )
                
                fig.add_trace(
                    go.Table(
                        header=dict(
                            values=list(enum_performance.keys()),
                            fill_color=colors['danger'],
                            font=dict(color='white', size=11, family='Arial Black'),
                            align='center'
                        ),
                        cells=dict(
                            values=list(enum_performance.values()),
                            fill_color='#fff3f3',
                            font=dict(color='#333', size=10),
                            align='center'
                        )
                    ),
                    row=10, col=1
                )
            
            # Update layout
            fig.update_layout(
                height=3500,
                showlegend=False,
                title={
                    'text': f'<b>{title}</b><br><sup>Last Updated: {datetime.now().strftime("%B %d, %Y %H:%M:%S")} | ⚠️ Minimum Valid Duration: 50 minutes | 🔄 Auto-Refresh Dashboard</sup>',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 26, 'color': '#333', 'family': 'Arial Black'}
                },
                template='plotly_white',
                font=dict(family="Arial, sans-serif", size=11),
                paper_bgcolor='#f8f9fa',
                plot_bgcolor='white',
                mapbox=dict(
                    style="open-street-map",
                    center=dict(
                        lat=self.df[lat_column].mean() if lat_column in self.df.columns else 0,
                        lon=self.df[lon_column].mean() if lon_column in self.df.columns else 0
                    ),
                    zoom=6
                )
            )
            
            # Update axes
            fig.update_xaxes(showgrid=True, gridcolor='#e0e0e0')
            fig.update_yaxes(showgrid=True, gridcolor='#e0e0e0')
            
            # Save dashboard
            fig.write_html(output_file)
            logger.info(f"✅ Enhanced dashboard successfully saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating dashboard: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _calculate_enumerator_performance_detailed(self, enum_col, duration_col, district_col, 
                                                   lat_col, lon_col, min_duration, max_duration):
        """Calculate detailed enumerator performance"""
        performance = {
            'Enumerator': [],
            'Total': [],
            '❌ Too Short': [],
            '⚠️ Too Long': [],
            'Districts': [],
            'GPS Coords': [],
            'Avg Duration': [],
            'Invalid %': []
        }
        
        enumerators = self.df[enum_col].value_counts().index
        
        for enum in enumerators:
            enum_data = self.df[self.df[enum_col] == enum]
            
            total = len(enum_data)
            too_short = enum_data['is_too_short'].sum() if 'is_too_short' in enum_data.columns else 0
            too_long = enum_data['is_too_long'].sum() if 'is_too_long' in enum_data.columns else 0
            avg_dur = enum_data[duration_col].mean()
            invalid_pct = (too_short / total * 100) if total > 0 else 0
            
            if district_col and district_col in enum_data.columns:
                districts = enum_data[district_col].value_counts().to_dict()
                district_str = ', '.join([f"{dist}({cnt})" for dist, cnt in districts.items()])
            else:
                district_str = 'N/A'
            
            if lat_col in enum_data.columns and lon_col in enum_data.columns:
                gps_data = enum_data[[lat_col, lon_col]].dropna()
                if len(gps_data) > 0:
                    gps_examples = []
                    for idx, row in gps_data.head(2).iterrows():
                        gps_examples.append(f"({row[lat_col]:.4f},{row[lon_col]:.4f})")
                    gps_str = ', '.join(gps_examples)
                    if len(gps_data) > 2:
                        gps_str += f' +{len(gps_data)-2} more'
                else:
                    gps_str = 'No GPS'
            else:
                gps_str = 'N/A'
            
            performance['Enumerator'].append(str(enum))
            performance['Total'].append(total)
            performance['❌ Too Short'].append(too_short)
            performance['⚠️ Too Long'].append(too_long)
            performance['Districts'].append(district_str)
            performance['GPS Coords'].append(gps_str)
            performance['Avg Duration'].append(f"{avg_dur:.0f}min")
            performance['Invalid %'].append(f"{invalid_pct:.1f}%")
        
        sorted_indices = sorted(range(len(performance['❌ Too Short'])), 
                               key=lambda i: performance['❌ Too Short'][i], 
                               reverse=True)
        
        for key in performance:
            performance[key] = [performance[key][i] for i in sorted_indices]
        
        max_rows = 15
        for key in performance:
            performance[key] = performance[key][:max_rows]
        
        return performance
    
    def _calculate_completion_stats(self, district_col, duration_col, enum_col):
        """Calculate completion statistics"""
        stats = {}
        
        stats['📊 Total Surveys'] = f"{len(self.df):,}"
        
        if 'is_valid' in self.df.columns:
            valid_count = self.df['is_valid'].sum()
            invalid_count = (~self.df['is_valid']).sum()
            valid_pct = (valid_count / len(self.df) * 100)
            stats['✅ Valid (≥50min)'] = f"{valid_count} ({valid_pct:.1f}%)"
            stats['❌ Invalid (<50min)'] = f"{invalid_count} ({100-valid_pct:.1f}%)"
        
        if district_col and district_col in self.df.columns:
            n_districts = self.df[district_col].nunique()
            stats['📍 Districts'] = f"{n_districts}"
        
        if enum_col and enum_col in self.df.columns:
            n_enums = self.df[enum_col].nunique()
            stats['👥 Enumerators'] = f"{n_enums}"
        
        if duration_col and duration_col in self.df.columns:
            avg_duration = self.df[duration_col].mean()
            stats['⏱️ Avg Duration'] = f"{avg_duration:.1f} min"
        
        if 'latitude' in self.df.columns and 'longitude' in self.df.columns:
            valid_gps = self.df[['latitude', 'longitude']].notna().all(axis=1).sum()
            gps_pct = (valid_gps / len(self.df) * 100)
            stats['📍 Valid GPS'] = f"{gps_pct:.1f}%"
        
        completeness = (1 - self.df.isnull().sum().sum() / (len(self.df) * len(self.df.columns))) * 100
        stats['✅ Data Complete'] = f"{completeness:.1f}%"
        
        if '_submission_time' in self.df.columns:
            date_range = f"{self.df['_submission_time'].min().strftime('%b %d')} - {self.df['_submission_time'].max().strftime('%b %d')}"
            stats['📅 Period'] = date_range
        
        return stats
    
    def _calculate_quality_score(self, duration_col, min_duration):
        """Calculate overall quality score"""
        if self.df is None or len(self.df) == 0:
            return 0
        
        scores = []
        
        completeness = (1 - self.df.isnull().sum().sum() / (len(self.df) * len(self.df.columns))) * 100
        scores.append(completeness * 0.30)
        
        if 'latitude' in self.df.columns and 'longitude' in self.df.columns:
            gps_valid = (self.df[['latitude', 'longitude']].notna().all(axis=1).sum() / len(self.df)) * 100
            scores.append(gps_valid * 0.25)
        
        if 'is_valid' in self.df.columns:
            valid_interviews = (self.df['is_valid'].sum() / len(self.df)) * 100
            scores.append(valid_interviews * 0.45)
        
        return round(sum(scores), 1)


if __name__ == "__main__":
    # Example usage with custom configuration
    config = {
        'district_targets': {
            'Bosaso': 100,
            'Dhusamareb': 100,
            'Beletweyne': 100,
            'Baki': 50,
            'Gabiley': 50
        },
        'beneficiary_ratio': 0.5,
        'max_duration': 120
    }
    
    dashboard = ONAQualityDashboard('ona_data_export.csv', config=config)
    if dashboard.load_data():
        dashboard.generate_dashboard()
