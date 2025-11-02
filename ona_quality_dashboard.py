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
        
        self.beneficiary_ratio = self.config.get('beneficiary_ratio', 0.5)
        
    def load_data(self):
        """Load data from CSV file"""
        try:
            self.df = pd.read_csv(self.data_file)
            logger.info(f"Loaded {len(self.df)} records from {self.data_file}")
            
            # Convert date columns
            date_columns = ['start', 'end', 'today', '_submission_time']
            for col in date_columns:
                if col in self.df.columns:
                    self.df[col] = pd.to_datetime(self.df[col], errors='coerce')
                    
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
    
    def _generate_alerts(self, enum_col, duration_col, district_col):
        """Generate real-time alerts - OPTIMIZED"""
        alerts = []
        
        # Check for today's invalid surveys
        if '_submission_time' in self.df.columns and 'is_valid' in self.df.columns:
            today = datetime.now().date()
            today_data = self.df[self.df['_submission_time'].dt.date == today]
            invalid_today = (~today_data['is_valid']).sum()
            if invalid_today > 0:
                alerts.append(f"⚠️ {invalid_today} invalid surveys submitted TODAY")
        
        # Check for enumerators with high invalid rate (only if >10 total surveys)
        if enum_col and enum_col in self.df.columns and 'is_valid' in self.df.columns:
            enum_stats = self.df.groupby(enum_col).agg({
                'is_valid': ['sum', 'count']
            })
            enum_stats.columns = ['valid', 'total']
            enum_stats = enum_stats[enum_stats['total'] >= 10]  # Only check active enumerators
            enum_stats['invalid_rate'] = (1 - enum_stats['valid'] / enum_stats['total']) * 100
            
            problem_enums = enum_stats[enum_stats['invalid_rate'] > 50].head(3)  # Top 3 only
            for enum_name, row in problem_enums.iterrows():
                alerts.append(f"🚨 '{enum_name}': {row['invalid_rate']:.0f}% invalid")
        
        # Check for missing GPS
        if 'latitude' in self.df.columns and 'longitude' in self.df.columns:
            missing_gps = self.df[['latitude', 'longitude']].isna().any(axis=1).sum()
            if missing_gps > 0:
                alerts.append(f"📍 {missing_gps} surveys missing GPS")
        
        # Check progress for districts far behind
        if district_col and district_col in self.df.columns:
            actual_counts = self.df[district_col].value_counts().to_dict()
            for district in self.target_districts[:3]:  # Check top 3 districts only
                target = self.district_targets.get(district, 100)
                actual = actual_counts.get(district, 0)
                progress_pct = (actual / target * 100) if target > 0 else 0
                
                if progress_pct < 50 and target > 0:
                    remaining = target - actual
                    alerts.append(f"🔴 {district}: {progress_pct:.0f}% - Need {remaining} more")
        
        return alerts[:8]  # Return top 8 alerts only
    
    def generate_dashboard(self, output_file='ona_dashboard_enhanced.html', 
                          title='ONA Data Quality Dashboard',
                          district_column='district',
                          duration_column='duration_minutes',
                          enumerator_column=None,
                          lat_column='latitude',
                          lon_column='longitude'):
        """Generate OPTIMIZED interactive HTML dashboard"""
        
        if self.df is None or len(self.df) == 0:
            logger.error("No data available")
            return False
        
        try:
            logger.info("🚀 Generating OPTIMIZED dashboard...")
            
            # Smart column detection
            district_column = self._find_column(district_column, ['district', 'District_id'])
            self.district_col = district_column
            enumerator_column = self._find_column(enumerator_column, ['enum', 'enumerator', 'interviewer'])
            
            min_duration_threshold = 50
            max_duration_threshold = 120
            
            # Mark validity
            if duration_column in self.df.columns:
                self.df['is_valid'] = self.df[duration_column] >= min_duration_threshold
                self.df['is_too_long'] = self.df[duration_column] > max_duration_threshold
                self.df['is_too_short'] = self.df[duration_column] < min_duration_threshold
            
            # Calculate key metrics ONCE
            progress_data = self._calculate_progress_tracker(district_column)
            alerts = self._generate_alerts(enumerator_column, duration_column, district_column)
            quality_dimensions = self._calculate_quality_dimensions(duration_column)
            
            # Create SIMPLIFIED figure with 6 rows (reduced from 10)
            fig = make_subplots(
                rows=6, cols=3,
                subplot_titles=(
                    '🎯 Progress Tracker', '🚨 Alerts', '⭐ Quality',
                    '📊 Districts', '⏱️ Duration', '👥 Enumerators',
                    '📍 GPS Map', '', '⚠️ Validity',
                    '📈 Daily Trends', '', '🔍 Missing Data',
                    '👥 Beneficiaries', '📋 Stats', '🎯 Score',
                    '⚠️ Enumerator Performance', '', ''
                ),
                specs=[
                    [{"type": "table"}, {"type": "table"}, {"type": "indicator"}],
                    [{"type": "bar"}, {"type": "box"}, {"type": "bar"}],
                    [{"type": "scattermapbox", "colspan": 2}, None, {"type": "bar"}],
                    [{"type": "scatter", "colspan": 2}, None, {"type": "bar"}],
                    [{"type": "table"}, {"type": "table"}, {"type": "indicator"}],
                    [{"type": "table", "colspan": 3}, None, None]
                ],
                row_heights=[0.15, 0.20, 0.20, 0.15, 0.15, 0.15],
                vertical_spacing=0.06,
                horizontal_spacing=0.10
            )
            
            colors = {'primary': '#667eea', 'success': '#4caf50', 'warning': '#ff9800', 
                     'danger': '#f44336', 'info': '#4facfe'}
            
            # ROW 1: Progress, Alerts, Quality Score
            logger.info("Adding row 1: Progress, Alerts, Quality...")
            if progress_data:
                fig.add_trace(go.Table(
                    header=dict(values=list(progress_data.keys()), fill_color=colors['primary'],
                               font=dict(color='white', size=11), align='center', height=28),
                    cells=dict(values=list(progress_data.values()), 
                              fill_color='#f0f4f8', font=dict(size=10), align='center', height=25)
                ), row=1, col=1)
            
            if alerts:
                fig.add_trace(go.Table(
                    header=dict(values=['<b>🚨 ALERTS</b>'], fill_color=colors['danger'],
                               font=dict(color='white', size=11), align='left', height=28),
                    cells=dict(values=[alerts], fill_color='#fff3f3',
                              font=dict(size=9), align='left', height=22)
                ), row=1, col=2)
            
            quality_score = self._calculate_quality_score(duration_column, min_duration_threshold)
            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=quality_score,
                title={'text': "<b>Quality</b>", 'font': {'size': 14}},
                gauge={'axis': {'range': [0, 100]}, 'bar': {'color': colors['primary']},
                       'steps': [{'range': [0, 60], 'color': '#ffebee'},
                                {'range': [60, 80], 'color': '#fff9c4'},
                                {'range': [80, 100], 'color': '#e8f5e9'}]}
            ), row=1, col=3)
            
            # ROW 2: Districts, Duration, Enumerators
            logger.info("Adding row 2: Core charts...")
            if district_column and district_column in self.df.columns:
                district_data = self.df[district_column].value_counts().sort_values(ascending=True)
                fig.add_trace(go.Bar(
                    y=district_data.index, x=district_data.values, orientation='h',
                    marker_color=colors['primary'], text=district_data.values, textposition='outside'
                ), row=2, col=1)
            
            if duration_column in self.df.columns:
                # Sample data for performance (max 1000 points)
                sample_df = self.df.sample(n=min(1000, len(self.df)))
                fig.add_trace(go.Box(
                    y=sample_df[duration_column], marker_color=colors['primary'], name='Duration'
                ), row=2, col=2)
                fig.add_hline(y=min_duration_threshold, line_color="red", line_width=2, row=2, col=2)
            
            if enumerator_column and enumerator_column in self.df.columns:
                enum_data = self.df[enumerator_column].value_counts().head(8)
                fig.add_trace(go.Bar(
                    x=enum_data.index, y=enum_data.values, marker_color=colors['info'],
                    text=enum_data.values, textposition='outside'
                ), row=2, col=3)
            
            # ROW 3: GPS Map & Validity
            logger.info("Adding row 3: Map & Validity...")
            if lat_column in self.df.columns and lon_column in self.df.columns:
                valid_gps = self.df.dropna(subset=[lat_column, lon_column])
                # Sample GPS points for performance (max 500 points)
                if len(valid_gps) > 500:
                    valid_gps = valid_gps.sample(n=500)
                
                fig.add_trace(go.Scattermapbox(
                    lat=valid_gps[lat_column], lon=valid_gps[lon_column],
                    mode='markers', marker=dict(size=6, color='#ff6b6b', opacity=0.6),
                    name='Interviews', hoverinfo='skip'
                ), row=3, col=1)
            
            if 'is_valid' in self.df.columns:
                valid = self.df['is_valid'].sum()
                invalid = (~self.df['is_valid']).sum()
                fig.add_trace(go.Bar(
                    x=['✅ Valid', '❌ Invalid'], y=[valid, invalid],
                    marker=dict(color=[colors['success'], colors['danger']]),
                    text=[valid, invalid], textposition='outside'
                ), row=3, col=3)
            
            # ROW 4: Daily Trends & Missing Data
            logger.info("Adding row 4: Trends & Missing...")
            if '_submission_time' in self.df.columns:
                daily_data = self.df.groupby(self.df['_submission_time'].dt.date).size()
                fig.add_trace(go.Scatter(
                    x=daily_data.index, y=daily_data.values,
                    mode='lines+markers', line=dict(color=colors['primary'], width=2),
                    fill='tozeroy', fillcolor='rgba(102, 126, 234, 0.2)'
                ), row=4, col=1)
            
            missing_data = (self.df.isnull().sum() / len(self.df) * 100).sort_values(ascending=False).head(6)
            missing_data = missing_data[missing_data > 0]
            if len(missing_data) > 0:
                display_names = [col.split('/')[-1][:20] if '/' in col else col[:20] for col in missing_data.index]
                fig.add_trace(go.Bar(
                    y=display_names, x=missing_data.values, orientation='h',
                    marker_color=colors['danger'], text=[f'{v:.0f}%' for v in missing_data.values],
                    textposition='outside'
                ), row=4, col=3)
            
            # ROW 5: Beneficiaries, Stats, Score Details
            logger.info("Adding row 5: Tables...")
            beneficiary_pivot = self._create_beneficiary_pivot_table()
            if beneficiary_pivot:
                fig.add_trace(go.Table(
                    header=dict(values=list(beneficiary_pivot.keys()), fill_color=colors['info'],
                               font=dict(color='white', size=11), align='center', height=28),
                    cells=dict(values=list(beneficiary_pivot.values()),
                              fill_color='#f0f4f8', font=dict(size=10), align='center', height=25)
                ), row=5, col=1)
            
            completion_data = self._calculate_completion_stats(district_column, duration_column, enumerator_column)
            fig.add_trace(go.Table(
                header=dict(values=['<b>Metric</b>', '<b>Value</b>'], fill_color=colors['primary'],
                           font=dict(color='white', size=11), align='left', height=28),
                cells=dict(values=[list(completion_data.keys()), list(completion_data.values())],
                          fill_color=[['#f0f4f8', '#ffffff'] * len(completion_data)],
                          font=dict(size=10), align='left', height=25)
            ), row=5, col=2)
            
            # ROW 6: Enumerator Performance
            logger.info("Adding row 6: Performance...")
            if enumerator_column and enumerator_column in self.df.columns:
                enum_performance = self._calculate_enumerator_performance_simple(
                    enumerator_column, duration_column, min_duration_threshold
                )
                fig.add_trace(go.Table(
                    header=dict(values=list(enum_performance.keys()), fill_color=colors['danger'],
                               font=dict(color='white', size=11), align='center', height=28),
                    cells=dict(values=list(enum_performance.values()),
                              fill_color='#fff3f3', font=dict(size=10), align='center', height=25)
                ), row=6, col=1)
            
            # Update layout - OPTIMIZED
            logger.info("Finalizing layout...")
            fig.update_layout(
                height=2200,  # Reduced from 3500
                showlegend=False,
                title={
                    'text': f'<b>{title}</b><br><sup>Updated: {datetime.now().strftime("%b %d, %Y %H:%M")} | Min Duration: 50 min</sup>',
                    'x': 0.5, 'xanchor': 'center',
                    'font': {'size': 24, 'color': '#333'}
                },
                template='plotly_white',
                font=dict(family="Arial", size=10),
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
            
            # Save
            logger.info("Writing HTML...")
            fig.write_html(output_file, config={'displayModeBar': False})  # Remove mode bar for speed
            logger.info(f"✅ Dashboard saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _calculate_progress_tracker(self, district_col):
        """Calculate progress - OPTIMIZED"""
        if not district_col or district_col not in self.df.columns:
            return None
        
        progress = {'District': [], 'Target': [], 'Actual': [], 'Status': []}
        actual_counts = self.df[district_col].value_counts().to_dict()
        
        for district in self.target_districts:
            target = self.district_targets.get(district, 100)
            actual = actual_counts.get(district, 0)
            progress_pct = min(100, (actual / target * 100) if target > 0 else 0)
            status = '✅' if progress_pct >= 100 else '🟡' if progress_pct >= 75 else '🟠' if progress_pct >= 50 else '🔴'
            
            progress['District'].append(district)
            progress['Target'].append(target)
            progress['Actual'].append(actual)
            progress['Status'].append(f"{status} {progress_pct:.0f}%")
        
        return progress
    
    def _calculate_quality_dimensions(self, duration_col):
        """Calculate quality - OPTIMIZED"""
        dimensions = {}
        completeness = (1 - self.df.isnull().sum().sum() / (len(self.df) * len(self.df.columns))) * 100
        dimensions['Completeness'] = completeness
        
        if 'is_valid' in self.df.columns:
            dimensions['Duration'] = (self.df['is_valid'].sum() / len(self.df)) * 100
        
        if 'latitude' in self.df.columns:
            dimensions['GPS'] = (self.df['latitude'].notna().sum() / len(self.df)) * 100
        
        return dimensions
    
    def _create_beneficiary_pivot_table(self):
        """Create beneficiary pivot - OPTIMIZED"""
        try:
            treatment_col = 'respondent_information/treatment'
            if treatment_col not in self.df.columns or not self.district_col:
                return None
            
            pivot = pd.crosstab(self.df[self.district_col], self.df[treatment_col], margins=True)
            
            result = {'District': list(pivot.index)}
            for col in pivot.columns:
                result[col] = list(pivot[col].values)
            return result
        except:
            return None
    
    def _calculate_enumerator_performance_simple(self, enum_col, duration_col, min_duration):
        """Simple enumerator performance - OPTIMIZED"""
        performance = {'Enumerator': [], 'Total': [], 'Invalid': [], 'Avg Duration': []}
        
        for enum in self.df[enum_col].value_counts().head(10).index:
            enum_data = self.df[self.df[enum_col] == enum]
            total = len(enum_data)
            invalid = (~enum_data['is_valid']).sum() if 'is_valid' in enum_data.columns else 0
            avg_dur = enum_data[duration_col].mean() if duration_col in enum_data.columns else 0
            
            performance['Enumerator'].append(str(enum))
            performance['Total'].append(total)
            performance['Invalid'].append(invalid)
            performance['Avg Duration'].append(f"{avg_dur:.0f}min")
        
        return performance
    
    def _calculate_completion_stats(self, district_col, duration_col, enum_col):
        """Stats - OPTIMIZED"""
        stats = {}
        stats['📊 Total'] = f"{len(self.df):,}"
        
        if 'is_valid' in self.df.columns:
            valid_pct = (self.df['is_valid'].sum() / len(self.df) * 100)
            stats['✅ Valid'] = f"{valid_pct:.0f}%"
        
        if district_col and district_col in self.df.columns:
            stats['📍 Districts'] = f"{self.df[district_col].nunique()}"
        
        if duration_col and duration_col in self.df.columns:
            stats['⏱️ Avg Duration'] = f"{self.df[duration_col].mean():.0f}min"
        
        return stats
    
    def _calculate_quality_score(self, duration_col, min_duration):
        """Quality score - OPTIMIZED"""
        scores = []
        completeness = (1 - self.df.isnull().sum().sum() / (len(self.df) * len(self.df.columns))) * 100
        scores.append(completeness * 0.4)
        
        if 'is_valid' in self.df.columns:
            scores.append((self.df['is_valid'].sum() / len(self.df)) * 100 * 0.6)
        
        return round(sum(scores), 1)


if __name__ == "__main__":
    config = {
        'district_targets': {'Bosaso': 100, 'Dhusamareb': 100, 'Beletweyne': 100, 'Baki': 50, 'Gabiley': 50},
        'beneficiary_ratio': 0.5
    }
    
    dashboard = ONAQualityDashboard('ona_data_export.csv', config=config)
    if dashboard.load_data():
        dashboard.generate_dashboard()
