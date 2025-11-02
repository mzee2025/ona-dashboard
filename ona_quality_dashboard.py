"""
Enhanced ONA Quality Dashboard with 15 Advanced Features
Complete monitoring solution for data collection quality
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from datetime import datetime, timedelta
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ONAQualityDashboard:
    def __init__(self, data_file, config=None):
        """Initialize enhanced dashboard with data file and optional config"""
        self.data_file = data_file
        self.config = config or {}
        self.df = None
        self.district_col = None
        self.target_districts = ['Bosaso', 'Dhusamareb', 'Beletweyne', 'Baki', 'Gabiley']
        
        # Default configuration
        self.config.setdefault('min_duration', 50)
        self.config.setdefault('max_duration', 120)
        self.config.setdefault('target_total', 1000)
        self.config.setdefault('quality_thresholds', {
            'completeness': 95,
            'accuracy': 90,
            'consistency': 85,
            'timeliness': 80,
            'validity': 90
        })
        
    def load_data(self):
        """Load data from CSV file"""
        try:
            self.df = pd.read_csv(self.data_file)
            logger.info(f"Loaded {len(self.df)} records")
            
            # Convert dates
            if '_submission_time' in self.df.columns:
                self.df['_submission_time'] = pd.to_datetime(self.df['_submission_time'], errors='coerce')
                self.df['submission_date'] = self.df['_submission_time'].dt.date
                self.df['submission_hour'] = self.df['_submission_time'].dt.hour
                self.df['submission_weekday'] = self.df['_submission_time'].dt.day_name()
                    
            return True
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False
    
    def _find_column(self, column_name, keywords):
        """Find column by keywords"""
        if column_name and column_name in self.df.columns:
            return column_name
        
        for col in self.df.columns:
            if any(keyword.lower() in col.lower() for keyword in keywords):
                logger.info(f"Found column '{col}' for {keywords}")
                return col
        return None
    
    def calculate_quality_scores(self):
        """Calculate 5-dimensional quality scores"""
        scores = {}
        
        # 1. Completeness (% of non-null values)
        non_null_pct = (1 - self.df.isnull().mean().mean()) * 100
        scores['completeness'] = round(non_null_pct, 1)
        
        # 2. Accuracy (based on duration validity)
        if 'duration_minutes' in self.df.columns:
            valid_duration = self.df['duration_minutes'].between(
                self.config['min_duration'], 
                self.config['max_duration']
            ).mean() * 100
            scores['accuracy'] = round(valid_duration, 1)
        else:
            scores['accuracy'] = 0
        
        # 3. Consistency (GPS coordinates present)
        if 'latitude' in self.df.columns and 'longitude' in self.df.columns:
            gps_valid = ((self.df['latitude'].notna()) & (self.df['longitude'].notna())).mean() * 100
            scores['consistency'] = round(gps_valid, 1)
        else:
            scores['consistency'] = 0
        
        # 4. Timeliness (submissions in last 24 hours)
        if '_submission_time' in self.df.columns:
            recent = (datetime.now() - self.df['_submission_time'].max()).total_seconds() / 3600
            timeliness = max(0, min(100, 100 - (recent / 24) * 50))
            scores['timeliness'] = round(timeliness, 1)
        else:
            scores['timeliness'] = 0
        
        # 5. Validity (overall data quality)
        if 'is_valid' in self.df.columns:
            scores['validity'] = round(self.df['is_valid'].mean() * 100, 1)
        else:
            scores['validity'] = scores['completeness']
        
        return scores
    
    def get_daily_summary(self):
        """Get summary statistics for today, yesterday, and this week"""
        summary = {}
        now = datetime.now()
        
        if '_submission_time' not in self.df.columns:
            return {
                'today': {'count': 0, 'valid': 0, 'avg_duration': 0},
                'yesterday': {'count': 0, 'valid': 0, 'avg_duration': 0},
                'this_week': {'count': 0, 'valid': 0, 'avg_duration': 0}
            }
        
        today = now.date()
        yesterday = (now - timedelta(days=1)).date()
        week_start = (now - timedelta(days=now.weekday())).date()
        
        for period_name, start_date, end_date in [
            ('today', today, today),
            ('yesterday', yesterday, yesterday),
            ('this_week', week_start, today)
        ]:
            mask = (self.df['submission_date'] >= start_date) & (self.df['submission_date'] <= end_date)
            period_data = self.df[mask]
            
            summary[period_name] = {
                'count': len(period_data),
                'valid': period_data['is_valid'].sum() if 'is_valid' in period_data.columns else 0,
                'avg_duration': round(period_data['duration_minutes'].mean(), 1) if 'duration_minutes' in period_data.columns else 0
            }
        
        return summary
    
    def get_real_time_alerts(self):
        """Generate real-time alerts based on quality issues"""
        alerts = []
        
        if len(self.df) == 0:
            return alerts
        
        # Check for recent invalid submissions
        if 'is_valid' in self.df.columns and '_submission_time' in self.df.columns:
            recent = self.df[self.df['_submission_time'] > datetime.now() - timedelta(hours=24)]
            if len(recent) > 0:
                invalid_pct = (1 - recent['is_valid'].mean()) * 100
                if invalid_pct > 20:
                    alerts.append({
                        'level': 'danger',
                        'message': f'{invalid_pct:.0f}% of last 24h submissions are invalid',
                        'icon': '⚠️'
                    })
        
        # Check for missing GPS
        if 'latitude' in self.df.columns:
            missing_gps_pct = (self.df['latitude'].isnull().mean()) * 100
            if missing_gps_pct > 10:
                alerts.append({
                    'level': 'warning',
                    'message': f'{missing_gps_pct:.0f}% of records missing GPS coordinates',
                    'icon': '📍'
                })
        
        # Check completion rate
        target_total = self.config.get('target_total', 1000)
        progress_pct = (len(self.df) / target_total) * 100
        if progress_pct < 50:
            alerts.append({
                'level': 'info',
                'message': f'Only {progress_pct:.0f}% of target reached ({len(self.df)}/{target_total})',
                'icon': '🎯'
            })
        
        return alerts
    
    def get_enumerator_leaderboard(self, enumerator_column):
        """Get top and bottom performing enumerators"""
        if not enumerator_column or enumerator_column not in self.df.columns:
            return {'top': [], 'bottom': []}
        
        enum_stats = self.df.groupby(enumerator_column).agg({
            '_id': 'count',
            'is_valid': 'mean',
            'duration_minutes': 'mean'
        }).round(2)
        
        enum_stats.columns = ['count', 'valid_rate', 'avg_duration']
        enum_stats['score'] = (enum_stats['valid_rate'] * 0.7 + 
                               (enum_stats['count'] / enum_stats['count'].max()) * 0.3)
        
        enum_stats = enum_stats.sort_values('score', ascending=False)
        
        return {
            'top': enum_stats.head(5).reset_index().to_dict('records'),
            'bottom': enum_stats.tail(5).reset_index().to_dict('records')
        }
    
    def get_beneficiary_balance(self):
        """Get beneficiary type distribution"""
        beneficiary_cols = [col for col in self.df.columns if 'beneficiary' in col.lower() or 'treatment' in col.lower()]
        
        if not beneficiary_cols:
            return {}
        
        col = beneficiary_cols[0]
        distribution = self.df[col].value_counts().to_dict()
        
        return {
            'distribution': distribution,
            'balance_score': min(distribution.values()) / max(distribution.values()) * 100 if distribution else 0
        }
    
    def get_time_patterns(self):
        """Analyze interview patterns by time"""
        if '_submission_time' not in self.df.columns:
            return {}
        
        # Peak hours
        hourly = self.df['submission_hour'].value_counts().sort_index()
        
        # Weekday vs Weekend
        self.df['is_weekend'] = self.df['_submission_time'].dt.dayofweek >= 5
        weekend_stats = {
            'weekend': len(self.df[self.df['is_weekend']]),
            'weekday': len(self.df[~self.df['is_weekend']])
        }
        
        return {
            'peak_hour': int(hourly.idxmax()) if len(hourly) > 0 else 0,
            'hourly_distribution': hourly.to_dict(),
            'weekend_vs_weekday': weekend_stats
        }
    
    def generate_dashboard(self, output_file='ona_dashboard.html', 
                          title='ONA Data Quality Dashboard - Enhanced',
                          district_column='district',
                          duration_column='duration_minutes',
                          enumerator_column=None):
        """Generate enhanced dashboard with all 15 features"""
        
        if self.df is None or len(self.df) == 0:
            logger.error("No data available")
            return False
        
        try:
            logger.info("🚀 Generating ENHANCED dashboard with 15 features...")
            
            # Find columns
            district_column = self._find_column(district_column, ['district', 'District_id'])
            self.district_col = district_column
            enumerator_column = self._find_column(enumerator_column, ['enum', 'enumerator'])
            
            # Mark validity
            min_duration_threshold = self.config['min_duration']
            if duration_column in self.df.columns:
                self.df['is_valid'] = self.df[duration_column] >= min_duration_threshold
            
            # Calculate metrics
            quality_scores = self.calculate_quality_scores()
            daily_summary = self.get_daily_summary()
            alerts = self.get_real_time_alerts()
            leaderboard = self.get_enumerator_leaderboard(enumerator_column)
            beneficiary_balance = self.get_beneficiary_balance()
            time_patterns = self.get_time_patterns()
            
            # Create figure with 5 rows for comprehensive display
            fig = make_subplots(
                rows=5, cols=3,
                subplot_titles=(
                    # Row 1: Summary Cards
                    '🎯 Progress Tracker',
                    '⚠️ Real-Time Alerts',
                    '📊 Daily Summary',
                    
                    # Row 2: Quality Breakdown
                    '⭐ Quality Score Breakdown',
                    '🏆 Top Enumerators',
                    '👥 Beneficiary Balance',
                    
                    # Row 3: Districts & Duration
                    '📍 Surveys by District',
                    '⏱️ Duration Distribution',
                    '🔍 Missing Data Patterns',
                    
                    # Row 4: Time Analysis
                    '🕐 Peak Hours Analysis',
                    '📈 Daily Trends',
                    '🗓️ Weekday vs Weekend',
                    
                    # Row 5: GPS & Performance
                    '🗺️ GPS Coverage Map',
                    '📋 Top Issues',
                    '💯 Performance Metrics'
                ),
                specs=[
                    [{"type": "indicator"}, {"type": "table"}, {"type": "table"}],
                    [{"type": "bar"}, {"type": "table"}, {"type": "pie"}],
                    [{"type": "bar"}, {"type": "box"}, {"type": "bar"}],
                    [{"type": "bar"}, {"type": "scatter"}, {"type": "bar"}],
                    [{"type": "scattermapbox"}, {"type": "table"}, {"type": "bar"}]
                ],
                row_heights=[0.15, 0.20, 0.20, 0.20, 0.25],
                vertical_spacing=0.08,
                horizontal_spacing=0.12
            )
            
            colors = {
                'primary': '#667eea',
                'success': '#4caf50',
                'danger': '#f44336',
                'warning': '#ff9800',
                'info': '#2196f3'
            }
            
            # ============== ROW 1: SUMMARY CARDS ==============
            
            # 1. PROGRESS TRACKER
            target = self.config.get('target_total', 1000)
            actual = len(self.df)
            progress_pct = (actual / target) * 100
            
            fig.add_trace(go.Indicator(
                mode="gauge+number+delta",
                value=actual,
                delta={'reference': target, 'valueformat': '.0f'},
                title={'text': f"<b>Target: {target}</b>"},
                gauge={
                    'axis': {'range': [0, target]},
                    'bar': {'color': colors['primary']},
                    'steps': [
                        {'range': [0, target*0.5], 'color': "#ffe0e0"},
                        {'range': [target*0.5, target*0.8], 'color': "#fff4e0"},
                        {'range': [target*0.8, target], 'color': "#e0ffe0"}
                    ],
                    'threshold': {
                        'line': {'color': colors['danger'], 'width': 4},
                        'thickness': 0.75,
                        'value': target
                    }
                }
            ), row=1, col=1)
            
            # 2. REAL-TIME ALERTS
            if alerts:
                alert_data = {
                    'Icon': [a['icon'] for a in alerts],
                    'Alert': [a['message'] for a in alerts]
                }
                fig.add_trace(go.Table(
                    header=dict(
                        values=['<b>⚠️</b>', '<b>Alert Message</b>'],
                        fill_color=colors['warning'],
                        font=dict(color='white', size=11),
                        align='left'
                    ),
                    cells=dict(
                        values=[alert_data['Icon'], alert_data['Alert']],
                        fill_color=[['#fff3cd'] * len(alerts)],
                        font=dict(size=10),
                        align='left',
                        height=25
                    )
                ), row=1, col=2)
            else:
                fig.add_trace(go.Table(
                    header=dict(
                        values=['<b>Status</b>'],
                        fill_color=colors['success'],
                        font=dict(color='white', size=11)
                    ),
                    cells=dict(
                        values=[['✅ No active alerts - All systems normal']],
                        fill_color='#d4edda',
                        font=dict(size=10),
                        align='center'
                    )
                ), row=1, col=2)
            
            # 3. DAILY SUMMARY
            summary_data = {
                'Period': ['Today', 'Yesterday', 'This Week'],
                'Count': [daily_summary['today']['count'], 
                         daily_summary['yesterday']['count'],
                         daily_summary['this_week']['count']],
                'Valid': [daily_summary['today']['valid'],
                         daily_summary['yesterday']['valid'],
                         daily_summary['this_week']['valid']],
                'Avg Duration': [f"{daily_summary['today']['avg_duration']}m",
                                f"{daily_summary['yesterday']['avg_duration']}m",
                                f"{daily_summary['this_week']['avg_duration']}m"]
            }
            fig.add_trace(go.Table(
                header=dict(
                    values=['<b>Period</b>', '<b>Count</b>', '<b>Valid</b>', '<b>Avg Duration</b>'],
                    fill_color=colors['primary'],
                    font=dict(color='white', size=11),
                    align='left'
                ),
                cells=dict(
                    values=list(summary_data.values()),
                    fill_color=[['#f0f4f8', '#ffffff', '#f0f4f8']],
                    font=dict(size=10),
                    align='left'
                )
            ), row=1, col=3)
            
            # ============== ROW 2: QUALITY & LEADERBOARD ==============
            
            # 4. QUALITY SCORE BREAKDOWN
            dimensions = ['Completeness', 'Accuracy', 'Consistency', 'Timeliness', 'Validity']
            scores = [quality_scores[k] for k in ['completeness', 'accuracy', 'consistency', 'timeliness', 'validity']]
            thresholds = [self.config['quality_thresholds'][k] for k in ['completeness', 'accuracy', 'consistency', 'timeliness', 'validity']]
            
            bar_colors = [colors['success'] if s >= t else colors['warning'] if s >= t-10 else colors['danger'] 
                         for s, t in zip(scores, thresholds)]
            
            fig.add_trace(go.Bar(
                x=dimensions,
                y=scores,
                text=[f"{s:.0f}%" for s in scores],
                textposition='outside',
                marker=dict(color=bar_colors),
                showlegend=False
            ), row=2, col=1)
            
            # Add threshold line
            fig.add_hline(y=85, line_dash="dash", line_color="gray", 
                         annotation_text="Target: 85%", row=2, col=1)
            
            # 5. TOP ENUMERATORS LEADERBOARD
            if leaderboard['top']:
                top_enum = leaderboard['top']
                leaderboard_data = {
                    'Rank': ['🥇', '🥈', '🥉', '4️⃣', '5️⃣'][:len(top_enum)],
                    'Enumerator': [e[enumerator_column][:20] for e in top_enum],
                    'Count': [e['count'] for e in top_enum],
                    'Valid %': [f"{e['valid_rate']*100:.0f}%" for e in top_enum]
                }
                fig.add_trace(go.Table(
                    header=dict(
                        values=['<b>Rank</b>', '<b>Enumerator</b>', '<b>Count</b>', '<b>Valid %</b>'],
                        fill_color=colors['success'],
                        font=dict(color='white', size=11),
                        align='left'
                    ),
                    cells=dict(
                        values=list(leaderboard_data.values()),
                        fill_color=[['#e8f5e9', '#f1f8e9', '#fffde7', '#fff9c4', '#fff59d'][:len(top_enum)]],
                        font=dict(size=10),
                        align='left'
                    )
                ), row=2, col=2)
            
            # 6. BENEFICIARY BALANCE
            if beneficiary_balance and 'distribution' in beneficiary_balance:
                dist = beneficiary_balance['distribution']
                fig.add_trace(go.Pie(
                    labels=list(dist.keys()),
                    values=list(dist.values()),
                    hole=0.4,
                    marker=dict(colors=['#667eea', '#4facfe', '#00f2fe', '#43e97b']),
                    textinfo='label+percent',
                    textposition='auto'
                ), row=2, col=3)
            
            # ============== ROW 3: DISTRICT & DURATION ==============
            
            # 7. SURVEYS BY DISTRICT
            if district_column and district_column in self.df.columns:
                district_data = self.df[district_column].value_counts().head(10)
                fig.add_trace(go.Bar(
                    x=district_data.index,
                    y=district_data.values,
                    marker_color=colors['primary'],
                    text=district_data.values,
                    textposition='outside',
                    showlegend=False
                ), row=3, col=1)
            
            # 8. DURATION DISTRIBUTION
            if duration_column in self.df.columns:
                sample_data = self.df[duration_column].dropna().sample(n=min(500, len(self.df)))
                fig.add_trace(go.Box(
                    y=sample_data,
                    marker_color=colors['primary'],
                    showlegend=False,
                    name='Duration'
                ), row=3, col=2)
                fig.add_hline(y=min_duration_threshold, line_color="red", line_width=2, 
                             annotation_text=f"Min: {min_duration_threshold}m", row=3, col=2)
            
            # 9. MISSING DATA PATTERNS
            missing_pct = (self.df.isnull().sum() / len(self.df) * 100).sort_values(ascending=False).head(10)
            if len(missing_pct) > 0:
                fig.add_trace(go.Bar(
                    y=[col[:30] for col in missing_pct.index],
                    x=missing_pct.values,
                    orientation='h',
                    marker_color=colors['warning'],
                    text=[f"{v:.1f}%" for v in missing_pct.values],
                    textposition='outside',
                    showlegend=False
                ), row=3, col=3)
            
            # ============== ROW 4: TIME ANALYSIS ==============
            
            # 10. PEAK HOURS ANALYSIS
            if time_patterns and 'hourly_distribution' in time_patterns:
                hourly = time_patterns['hourly_distribution']
                hours = sorted(hourly.keys())
                counts = [hourly[h] for h in hours]
                
                fig.add_trace(go.Bar(
                    x=hours,
                    y=counts,
                    marker_color='#4facfe',
                    text=counts,
                    textposition='outside',
                    showlegend=False
                ), row=4, col=1)
            
            # 11. DAILY TRENDS
            if 'submission_date' in self.df.columns:
                daily_counts = self.df['submission_date'].value_counts().sort_index()
                fig.add_trace(go.Scatter(
                    x=daily_counts.index,
                    y=daily_counts.values,
                    mode='lines+markers',
                    line=dict(color=colors['primary'], width=2),
                    fill='tozeroy',
                    showlegend=False
                ), row=4, col=2)
            
            # 12. WEEKDAY VS WEEKEND
            if time_patterns and 'weekend_vs_weekday' in time_patterns:
                ww = time_patterns['weekend_vs_weekday']
                fig.add_trace(go.Bar(
                    x=['Weekday', 'Weekend'],
                    y=[ww['weekday'], ww['weekend']],
                    marker_color=[colors['primary'], colors['info']],
                    text=[ww['weekday'], ww['weekend']],
                    textposition='outside',
                    showlegend=False
                ), row=4, col=3)
            
            # ============== ROW 5: GPS & FINAL METRICS ==============
            
            # 13. GPS MAP
            if 'latitude' in self.df.columns and 'longitude' in self.df.columns:
                valid_gps = self.df[self.df['latitude'].notna() & self.df['longitude'].notna()].sample(n=min(200, len(self.df)))
                
                if len(valid_gps) > 0:
                    fig.add_trace(go.Scattermapbox(
                        lat=valid_gps['latitude'],
                        lon=valid_gps['longitude'],
                        mode='markers',
                        marker=dict(size=8, color=colors['primary']),
                        text=valid_gps[district_column] if district_column in valid_gps.columns else 'Location',
                        showlegend=False
                    ), row=5, col=1)
            
            # 14. TOP ISSUES SUMMARY
            issues = []
            if 'is_valid' in self.df.columns:
                invalid_count = (~self.df['is_valid']).sum()
                if invalid_count > 0:
                    issues.append(('⚠️ Invalid Duration', invalid_count))
            
            if 'latitude' in self.df.columns:
                missing_gps = self.df['latitude'].isnull().sum()
                if missing_gps > 0:
                    issues.append(('📍 Missing GPS', missing_gps))
            
            if issues:
                fig.add_trace(go.Table(
                    header=dict(
                        values=['<b>Issue Type</b>', '<b>Count</b>'],
                        fill_color=colors['danger'],
                        font=dict(color='white', size=11),
                        align='left'
                    ),
                    cells=dict(
                        values=[[i[0] for i in issues], [i[1] for i in issues]],
                        fill_color='#ffebee',
                        font=dict(size=10),
                        align='left'
                    )
                ), row=5, col=2)
            
            # 15. PERFORMANCE METRICS
            metrics = {
                'Metric': ['Total Surveys', 'Valid %', 'Avg Duration', 'GPS Coverage', 'Quality Score'],
                'Value': [
                    f"{len(self.df):,}",
                    f"{self.df['is_valid'].mean()*100:.0f}%" if 'is_valid' in self.df.columns else 'N/A',
                    f"{self.df['duration_minutes'].mean():.0f}m" if 'duration_minutes' in self.df.columns else 'N/A',
                    f"{(1-self.df['latitude'].isnull().mean())*100:.0f}%" if 'latitude' in self.df.columns else 'N/A',
                    f"{sum(quality_scores.values())/len(quality_scores):.0f}%"
                ]
            }
            fig.add_trace(go.Table(
                header=dict(
                    values=['<b>Metric</b>', '<b>Value</b>'],
                    fill_color=colors['primary'],
                    font=dict(color='white', size=11),
                    align='left'
                ),
                cells=dict(
                    values=list(metrics.values()),
                    fill_color=[['#f0f4f8', '#ffffff'] * 3],
                    font=dict(size=10),
                    align='left'
                )
            ), row=5, col=3)
            
            # Update layout
            fig.update_layout(
                height=2000,
                showlegend=False,
                title={
                    'text': f'<b>{title}</b><br><sup>Last Updated: {datetime.now().strftime("%b %d, %Y %H:%M")} | Data Freshness: ✅ Live</sup>',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 24, 'color': '#333'}
                },
                template='plotly_white',
                paper_bgcolor='#f8f9fa',
                plot_bgcolor='white',
                mapbox=dict(
                    style="open-street-map",
                    center=dict(
                        lat=self.df['latitude'].mean() if 'latitude' in self.df.columns else 0,
                        lon=self.df['longitude'].mean() if 'longitude' in self.df.columns else 0
                    ),
                    zoom=6
                )
            )
            
            # Update axes
            fig.update_xaxes(showgrid=True, gridcolor='#e0e0e0')
            fig.update_yaxes(showgrid=True, gridcolor='#e0e0e0')
            
            # Save
            fig.write_html(output_file, config={'displayModeBar': True})
            logger.info(f"✅ ENHANCED Dashboard saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


if __name__ == "__main__":
    dashboard = ONAQualityDashboard('ona_data_export.csv')
    if dashboard.load_data():
        dashboard.generate_dashboard()
        print("\n✅ ENHANCED DASHBOARD COMPLETE! Open ona_dashboard.html to view")
