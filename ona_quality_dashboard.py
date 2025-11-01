import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ONAQualityDashboard:
    def __init__(self, data_file):
        """Initialize dashboard with data file"""
        self.data_file = data_file
        self.df = None
        
    def load_data(self):
        """Load data from CSV file"""
        try:
            self.df = pd.read_csv(self.data_file)
            logger.info(f"Loaded {len(self.df)} records from {self.data_file}")
            
            # Convert date columns
            if 'start' in self.df.columns:
                self.df['start'] = pd.to_datetime(self.df['start'])
            if 'end' in self.df.columns:
                self.df['end'] = pd.to_datetime(self.df['end'])
            if 'today' in self.df.columns:
                self.df['today'] = pd.to_datetime(self.df['today'])
                
            return True
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False
    
    def generate_dashboard(self, output_file='ona_dashboard.html', 
                          title='ONA Data Quality Dashboard',
                          district_column='district',
                          duration_column='duration_minutes',
                          enumerator_column=None):
        """Generate interactive HTML dashboard with quality metrics"""
        
        if self.df is None or len(self.df) == 0:
            logger.error("No data available to generate dashboard")
            return False
        
        try:
            # Create subplots
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=(
                    'Survey Completion Rate by District',
                    'Interview Duration Distribution',
                    'Missing Data Analysis',
                    'GPS Coordinates Verification',
                    'Daily Submission Trends',
                    'Data Quality Score'
                ),
                specs=[
                    [{"type": "bar"}, {"type": "histogram"}],
                    [{"type": "bar"}, {"type": "scatter"}],
                    [{"type": "scatter"}, {"type": "indicator"}]
                ],
                vertical_spacing=0.12,
                horizontal_spacing=0.15
            )
            
            # 1. Completion Rate by District
            if district_column in self.df.columns:
                district_counts = self.df[district_column].value_counts()
                fig.add_trace(
                    go.Bar(
                        x=district_counts.index,
                        y=district_counts.values,
                        name='Surveys',
                        marker_color='lightblue',
                        text=district_counts.values,
                        textposition='auto'
                    ),
                    row=1, col=1
                )
            
            # 2. Interview Duration Distribution
            if duration_column in self.df.columns:
                fig.add_trace(
                    go.Histogram(
                        x=self.df[duration_column],
                        name='Duration',
                        marker_color='lightgreen',
                        nbinsx=20
                    ),
                    row=1, col=2
                )
            
            # 3. Missing Data Analysis
            missing_data = (self.df.isnull().sum() / len(self.df) * 100).sort_values(ascending=False)[:10]
            fig.add_trace(
                go.Bar(
                    y=missing_data.index,
                    x=missing_data.values,
                    orientation='h',
                    name='Missing %',
                    marker_color='coral',
                    text=[f'{v:.1f}%' for v in missing_data.values],
                    textposition='auto'
                ),
                row=2, col=1
            )
            
            # 4. GPS Coordinates Verification
            if 'latitude' in self.df.columns and 'longitude' in self.df.columns:
                valid_gps = self.df.dropna(subset=['latitude', 'longitude'])
                fig.add_trace(
                    go.Scattermap(
                        lat=valid_gps['latitude'],
                        lon=valid_gps['longitude'],
                        mode='markers',
                        marker=dict(size=8, color='red'),
                        name='Survey Locations',
                        text=valid_gps.get(district_column, 'Location')
                    ),
                    row=2, col=2
                )
            
            # 5. Daily Submission Trends
            if 'start' in self.df.columns:
                daily_submissions = self.df.groupby(self.df['start'].dt.date).size()
                fig.add_trace(
                    go.Scatter(
                        x=daily_submissions.index,
                        y=daily_submissions.values,
                        mode='lines+markers',
                        name='Submissions',
                        line=dict(color='purple', width=2),
                        marker=dict(size=8)
                    ),
                    row=3, col=1
                )
            
            # 6. Overall Data Quality Score
            quality_score = self._calculate_quality_score()
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=quality_score,
                    title={'text': "Quality Score"},
                    delta={'reference': 80},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 50], 'color': "lightgray"},
                            {'range': [50, 75], 'color': "yellow"},
                            {'range': [75, 100], 'color': "lightgreen"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 90
                        }
                    }
                ),
                row=3, col=2
            )
            
            # Update layout
            fig.update_layout(
                height=1400,
                showlegend=False,
                title_text=title,
                title_x=0.5,
                title_font_size=24,
                mapbox=dict(
                    style="open-street-map",
                    center=dict(lat=-1.2921, lon=36.8219),  # Kenya coordinates
                    zoom=6
                )
            )
            
            # Update axes labels
            fig.update_xaxes(title_text="District", row=1, col=1)
            fig.update_yaxes(title_text="Number of Surveys", row=1, col=1)
            
            fig.update_xaxes(title_text="Duration (minutes)", row=1, col=2)
            fig.update_yaxes(title_text="Frequency", row=1, col=2)
            
            fig.update_xaxes(title_text="Missing Percentage (%)", row=2, col=1)
            fig.update_yaxes(title_text="Fields", row=2, col=1)
            
            fig.update_xaxes(title_text="Date", row=3, col=1)
            fig.update_yaxes(title_text="Number of Submissions", row=3, col=1)
            
            # Save dashboard
            fig.write_html(output_file)
            logger.info(f"Dashboard successfully saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating dashboard: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _calculate_quality_score(self):
        """Calculate overall data quality score (0-100)"""
        if self.df is None or len(self.df) == 0:
            return 0
        
        # Factors for quality score
        completeness = (1 - self.df.isnull().sum().sum() / (len(self.df) * len(self.df.columns))) * 100
        
        # GPS validity
        gps_valid = 0
        if 'latitude' in self.df.columns and 'longitude' in self.df.columns:
            gps_valid = (self.df[['latitude', 'longitude']].notna().all(axis=1).sum() / len(self.df)) * 100
        
        # Duration validity (assuming 10-120 minutes is valid)
        duration_valid = 100
        if 'duration_minutes' in self.df.columns:
            valid_durations = self.df['duration_minutes'].between(10, 120).sum()
            duration_valid = (valid_durations / len(self.df)) * 100
        
        # Weighted average
        quality_score = (completeness * 0.4 + gps_valid * 0.3 + duration_valid * 0.3)
        
        return round(quality_score, 1)


if __name__ == "__main__":
    # Test the dashboard
    dashboard = ONAQualityDashboard('ona_data_export.csv')
    if dashboard.load_data():
        dashboard.generate_dashboard()