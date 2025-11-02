import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from datetime import datetime
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ONAQualityDashboard:
    def __init__(self, data_file, config=None):
        """Initialize dashboard with data file and optional config"""
        self.data_file = data_file
        self.config = config or {}
        self.df = None
        
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
    
    def generate_dashboard(self, output_file='ona_dashboard.html', 
                          title='ONA Data Quality Dashboard',
                          district_column='district',
                          duration_column='duration_minutes',
                          enumerator_column=None,
                          lat_column='latitude',
                          lon_column='longitude'):
        """Generate beautiful interactive HTML dashboard"""
        
        if self.df is None or len(self.df) == 0:
            logger.error("No data available to generate dashboard")
            return False
        
        try:
            # Clean column names - handle nested structure
            if district_column not in self.df.columns:
                district_cols = [col for col in self.df.columns if 'district' in col.lower()]
                if district_cols:
                    district_column = district_cols[0]
            
            if enumerator_column and enumerator_column not in self.df.columns:
                enum_cols = [col for col in self.df.columns if 'enum' in col.lower()]
                if enum_cols:
                    enumerator_column = enum_cols[0]
            
            # Create figure with subplots
            fig = make_subplots(
                rows=4, cols=3,
                subplot_titles=(
                    '📊 Surveys by District',
                    '⏱️ Interview Duration (Minutes)',
                    '👥 Submissions by Enumerator',
                    '📍 Interview Locations Map',
                    '📈 Daily Submission Trends',
                    '⚠️ Duration Quality Flags',
                    '📋 Top Missing Data Fields',
                    '✅ Completion Status',
                    '📊 Overall Quality Score'
                ),
                specs=[
                    [{"type": "bar"}, {"type": "box"}, {"type": "bar"}],
                    [{"type": "scattermapbox", "colspan": 2}, None, {"type": "bar"}],
                    [{"type": "scatter", "colspan": 2}, None, {"type": "bar"}],
                    [{"type": "table", "colspan": 2}, None, {"type": "indicator"}]
                ],
                row_heights=[0.20, 0.30, 0.25, 0.25],
                vertical_spacing=0.08,
                horizontal_spacing=0.12
            )
            
            # 1. SURVEYS BY DISTRICT (Bar Chart)
            if district_column in self.df.columns:
                district_data = self.df[district_column].value_counts().sort_values(ascending=True)
                colors = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe']
                
                fig.add_trace(
                    go.Bar(
                        y=district_data.index,
                        x=district_data.values,
                        orientation='h',
                        marker=dict(
                            color=colors[:len(district_data)],
                            line=dict(color='white', width=2)
                        ),
                        text=district_data.values,
                        textposition='outside',
                        textfont=dict(size=14, color='#333', family='Arial Black'),
                        hovertemplate='<b>%{y}</b><br>Surveys: %{x}<extra></extra>'
                    ),
                    row=1, col=1
                )
            
            # 2. INTERVIEW DURATION BOX PLOT
            if duration_column in self.df.columns:
                fig.add_trace(
                    go.Box(
                        y=self.df[duration_column],
                        name='Duration',
                        marker=dict(color='#667eea'),
                        boxmean='sd',
                        fillcolor='rgba(102, 126, 234, 0.3)',
                        line=dict(color='#667eea', width=2),
                        hovertemplate='<b>Duration:</b> %{y:.1f} min<extra></extra>'
                    ),
                    row=1, col=2
                )
                
                # Add reference lines for thresholds
                min_dur = self.config.get('min_duration', 30)
                max_dur = self.config.get('max_duration', 120)
                
                fig.add_hline(y=min_dur, line_dash="dash", line_color="orange", 
                             annotation_text=f"Min: {min_dur} min", row=1, col=2)
                fig.add_hline(y=max_dur, line_dash="dash", line_color="red",
                             annotation_text=f"Max: {max_dur} min", row=1, col=2)
            
            # 3. SUBMISSIONS BY ENUMERATOR
            if enumerator_column and enumerator_column in self.df.columns:
                enum_data = self.df[enumerator_column].value_counts().head(10)
                
                fig.add_trace(
                    go.Bar(
                        x=enum_data.index,
                        y=enum_data.values,
                        marker=dict(
                            color='#4facfe',
                            line=dict(color='white', width=2)
                        ),
                        text=enum_data.values,
                        textposition='outside',
                        textfont=dict(size=12, color='#333'),
                        hovertemplate='<b>%{x}</b><br>Surveys: %{y}<extra></extra>'
                    ),
                    row=1, col=3
                )
            
            # 4. GPS LOCATIONS MAP
            if lat_column in self.df.columns and lon_column in self.df.columns:
                valid_gps = self.df.dropna(subset=[lat_column, lon_column])
                
                if len(valid_gps) > 0:
                    # Create hover text with district info
                    hover_text = []
                    for idx, row in valid_gps.iterrows():
                        dist = row.get(district_column, 'Unknown')
                        enum = row.get(enumerator_column, 'Unknown') if enumerator_column else 'Unknown'
                        text = f"<b>District:</b> {dist}<br><b>Enumerator:</b> {enum}"
                        hover_text.append(text)
                    
                    fig.add_trace(
                        go.Scattermapbox(
                            lat=valid_gps[lat_column],
                            lon=valid_gps[lon_column],
                            mode='markers',
                            marker=dict(
                                size=10,
                                color='#ff6b6b',
                                opacity=0.8,
                                sizemode='diameter'
                            ),
                            text=hover_text,
                            hovertemplate='%{text}<extra></extra>',
                            name='Interviews'
                        ),
                        row=2, col=1
                    )
            
            # 5. DAILY SUBMISSION TRENDS
            if '_submission_time' in self.df.columns:
                daily_data = self.df.groupby(self.df['_submission_time'].dt.date).size()
                
                fig.add_trace(
                    go.Scatter(
                        x=daily_data.index,
                        y=daily_data.values,
                        mode='lines+markers',
                        line=dict(color='#667eea', width=3),
                        marker=dict(size=10, color='#764ba2', line=dict(color='white', width=2)),
                        fill='tozeroy',
                        fillcolor='rgba(102, 126, 234, 0.2)',
                        hovertemplate='<b>Date:</b> %{x}<br><b>Submissions:</b> %{y}<extra></extra>'
                    ),
                    row=3, col=1
                )
            
            # 6. DURATION QUALITY FLAGS
            if duration_column in self.df.columns:
                min_dur = self.config.get('min_duration', 30)
                max_dur = self.config.get('max_duration', 120)
                
                too_short = len(self.df[self.df[duration_column] < min_dur])
                too_long = len(self.df[self.df[duration_column] > max_dur])
                good = len(self.df[(self.df[duration_column] >= min_dur) & 
                                  (self.df[duration_column] <= max_dur)])
                
                fig.add_trace(
                    go.Bar(
                        x=['Good', 'Too Short', 'Too Long'],
                        y=[good, too_short, too_long],
                        marker=dict(
                            color=['#4caf50', '#ff9800', '#f44336'],
                            line=dict(color='white', width=2)
                        ),
                        text=[good, too_short, too_long],
                        textposition='outside',
                        hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
                    ),
                    row=2, col=3
                )
            
            # 7. MISSING DATA ANALYSIS
            missing_data = (self.df.isnull().sum() / len(self.df) * 100).sort_values(ascending=False).head(8)
            missing_data = missing_data[missing_data > 0]
            
            if len(missing_data) > 0:
                fig.add_trace(
                    go.Bar(
                        y=missing_data.index,
                        x=missing_data.values,
                        orientation='h',
                        marker=dict(
                            color='#ff6b6b',
                            line=dict(color='white', width=2)
                        ),
                        text=[f'{v:.1f}%' for v in missing_data.values],
                        textposition='outside',
                        hovertemplate='<b>%{y}</b><br>Missing: %{x:.1f}%<extra></extra>'
                    ),
                    row=3, col=3
                )
            
            # 8. COMPLETION STATUS TABLE
            completion_data = self._calculate_completion_stats(
                district_column, duration_column, enumerator_column
            )
            
            fig.add_trace(
                go.Table(
                    header=dict(
                        values=['<b>Metric</b>', '<b>Value</b>'],
                        fill_color='#667eea',
                        font=dict(color='white', size=14, family='Arial Black'),
                        align='left',
                        height=35
                    ),
                    cells=dict(
                        values=[
                            list(completion_data.keys()),
                            list(completion_data.values())
                        ],
                        fill_color=[['#f0f4f8', '#ffffff'] * len(completion_data)],
                        font=dict(color='#333', size=13),
                        align='left',
                        height=30
                    )
                ),
                row=4, col=1
            )
            
            # 9. QUALITY SCORE GAUGE
            quality_score = self._calculate_quality_score(duration_column)
            
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=quality_score,
                    title={'text': "<b>Quality Score</b>", 'font': {'size': 20, 'color': '#333'}},
                    delta={'reference': 85, 'increasing': {'color': '#4caf50'}},
                    gauge={
                        'axis': {'range': [0, 100], 'tickwidth': 2, 'tickcolor': "#333"},
                        'bar': {'color': "#667eea", 'thickness': 0.75},
                        'bgcolor': "white",
                        'borderwidth': 2,
                        'bordercolor': "#ccc",
                        'steps': [
                            {'range': [0, 50], 'color': '#ffebee'},
                            {'range': [50, 75], 'color': '#fff9c4'},
                            {'range': [75, 100], 'color': '#e8f5e9'}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 90
                        }
                    },
                    number={'font': {'size': 50, 'color': '#333'}}
                ),
                row=4, col=3
            )
            
            # Update layout with professional styling
            fig.update_layout(
                height=1600,
                showlegend=False,
                title={
                    'text': f'<b>{title}</b><br><sup>Last Updated: {datetime.now().strftime("%B %d, %Y %H:%M:%S")}</sup>',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 28, 'color': '#333', 'family': 'Arial Black'}
                },
                template='plotly_white',
                font=dict(family="Arial, sans-serif", size=12),
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
            fig.update_xaxes(showgrid=True, gridcolor='#e0e0e0', title_font=dict(size=12, color='#333'))
            fig.update_yaxes(showgrid=True, gridcolor='#e0e0e0', title_font=dict(size=12, color='#333'))
            
            # Update subplot titles
            for annotation in fig['layout']['annotations']:
                annotation['font'] = dict(size=14, color='#333', family='Arial Black')
            
            # Save dashboard
            fig.write_html(output_file)
            logger.info(f"Dashboard successfully saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating dashboard: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _calculate_completion_stats(self, district_col, duration_col, enum_col):
        """Calculate comprehensive completion statistics"""
        stats = {}
        
        stats['📊 Total Surveys'] = f"{len(self.df):,}"
        
        if district_col in self.df.columns:
            stats['📍 Districts'] = f"{self.df[district_col].nunique()}"
        
        if enum_col and enum_col in self.df.columns:
            stats['👥 Enumerators'] = f"{self.df[enum_col].nunique()}"
        
        if duration_col in self.df.columns:
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
    
    def _calculate_quality_score(self, duration_col):
        """Calculate overall data quality score (0-100)"""
        if self.df is None or len(self.df) == 0:
            return 0
        
        scores = []
        
        # Completeness score
        completeness = (1 - self.df.isnull().sum().sum() / (len(self.df) * len(self.df.columns))) * 100
        scores.append(completeness * 0.35)
        
        # GPS validity score
        if 'latitude' in self.df.columns and 'longitude' in self.df.columns:
            gps_valid = (self.df[['latitude', 'longitude']].notna().all(axis=1).sum() / len(self.df)) * 100
            scores.append(gps_valid * 0.25)
        
        # Duration validity score
        if duration_col in self.df.columns:
            min_dur = self.config.get('min_duration', 30)
            max_dur = self.config.get('max_duration', 120)
            valid_durations = self.df[duration_col].between(min_dur, max_dur).sum()
            duration_score = (valid_durations / len(self.df)) * 100
            scores.append(duration_score * 0.40)
        
        return round(sum(scores), 1)


if __name__ == "__main__":
    dashboard = ONAQualityDashboard('ona_data_export.csv')
    if dashboard.load_data():
        dashboard.generate_dashboard()
