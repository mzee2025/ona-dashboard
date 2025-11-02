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
    
    def _find_column(self, column_name, keywords):
        """Find a column by searching for keywords in column names"""
        if column_name and column_name in self.df.columns:
            return column_name
        
        # Search for column with keywords
        for col in self.df.columns:
            col_lower = col.lower()
            if any(keyword.lower() in col_lower for keyword in keywords):
                logger.info(f"Found column '{col}' for {keywords}")
                return col
        
        return None
    
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
            # Smart column detection - find the actual columns in your data
            district_column = self._find_column(district_column, ['district', 'District_id'])
            enumerator_column = self._find_column(enumerator_column, ['enum', 'enumerator', 'interviewer'])
            treatment_column = self._find_column(None, ['treatment', 'beneficiary', 'group'])
            
            # CRITICAL: Update minimum duration threshold to 50 minutes
            min_duration_threshold = 50  # Interviews under 50 min are INVALID
            max_duration_threshold = self.config.get('max_duration', 120)
            
            logger.info(f"Using columns - District: {district_column}, Enumerator: {enumerator_column}, Treatment: {treatment_column}, Duration: {duration_column}")
            logger.info(f"Duration thresholds: MIN={min_duration_threshold} min (INVALID if below), MAX={max_duration_threshold} min")
            
            # Mark invalid interviews (duration < 50 min)
            if duration_column in self.df.columns:
                self.df['is_valid'] = self.df[duration_column] >= min_duration_threshold
                self.df['is_too_long'] = self.df[duration_column] > max_duration_threshold
                self.df['is_too_short'] = self.df[duration_column] < min_duration_threshold
                
                n_invalid = (~self.df['is_valid']).sum()
                n_valid = self.df['is_valid'].sum()
                n_too_long = self.df['is_too_long'].sum()
                logger.info(f"VALIDITY CHECK: {n_valid} valid, {n_invalid} INVALID (<50min), {n_too_long} too long (>120min)")
            
            # Create figure with subplots - NOW WITH 6 ROWS
            fig = make_subplots(
                rows=6, cols=3,
                subplot_titles=(
                    '📊 Surveys by District',
                    '⏱️ Interview Duration (Minutes)',
                    '👥 Submissions by Enumerator',
                    '📍 Interview Locations Map',
                    '📈 Daily Submission Trends',
                    '⚠️ Interview Validity Status',
                    '📋 Top Missing Data Fields',
                    '✅ Completion Status',
                    '📊 Overall Quality Score',
                    '👥 Beneficiary vs Non-Beneficiary by District',
                    '',
                    '',
                    '⚠️ Enumerator Performance: Invalid Interviews with Location Details',
                    '',
                    ''
                ),
                specs=[
                    [{"type": "bar"}, {"type": "box"}, {"type": "bar"}],
                    [{"type": "scattermapbox", "colspan": 2}, None, {"type": "bar"}],
                    [{"type": "scatter", "colspan": 2}, None, {"type": "bar"}],
                    [{"type": "table", "colspan": 2}, None, {"type": "indicator"}],
                    [{"type": "table", "colspan": 3}, None, None],
                    [{"type": "table", "colspan": 3}, None, None]
                ],
                row_heights=[0.15, 0.22, 0.18, 0.15, 0.15, 0.15],
                vertical_spacing=0.05,
                horizontal_spacing=0.12
            )
            
            # Color palette for districts
            district_colors = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe', 
                              '#43e97b', '#fa709a', '#fee140', '#30cfd0', '#a8edea']
            
            # 1. SURVEYS BY DISTRICT (Bar Chart)
            if district_column and district_column in self.df.columns:
                district_data = self.df[district_column].value_counts().sort_values(ascending=True)
                
                logger.info(f"District counts: {dict(district_data)}")
                
                colors_for_districts = [district_colors[i % len(district_colors)] for i in range(len(district_data))]
                
                fig.add_trace(
                    go.Bar(
                        y=district_data.index,
                        x=district_data.values,
                        orientation='h',
                        marker=dict(
                            color=colors_for_districts,
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
                
                fig.add_hline(y=min_duration_threshold, line_dash="solid", line_color="red", line_width=3,
                             annotation_text=f"⚠️ INVALID BELOW {min_duration_threshold} min", 
                             annotation_position="right",
                             row=1, col=2)
                
                fig.add_hline(y=max_duration_threshold, line_dash="dash", line_color="orange",
                             annotation_text=f"Max: {max_duration_threshold} min", row=1, col=2)
            
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
                    hover_text = []
                    for idx, row in valid_gps.iterrows():
                        dist = row.get(district_column, 'Unknown') if district_column else 'Unknown'
                        enum = row.get(enumerator_column, 'Unknown') if enumerator_column else 'Unknown'
                        dur = row.get(duration_column, 'N/A')
                        is_valid = row.get('is_valid', True)
                        validity_status = "✅ VALID" if is_valid else "❌ INVALID"
                        
                        if isinstance(dur, (int, float)):
                            text = f"<b>District:</b> {dist}<br><b>Enumerator:</b> {enum}<br><b>Duration:</b> {dur:.1f} min<br><b>Status:</b> {validity_status}"
                        else:
                            text = f"<b>District:</b> {dist}<br><b>Enumerator:</b> {enum}<br><b>Status:</b> {validity_status}"
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
            
            # 6. INTERVIEW VALIDITY STATUS
            if duration_column in self.df.columns:
                invalid = (~self.df['is_valid']).sum()
                valid = self.df['is_valid'].sum()
                too_long = self.df['is_too_long'].sum()
                
                fig.add_trace(
                    go.Bar(
                        x=['✅ Valid\n(≥50 min)', '❌ Invalid\n(<50 min)', '⚠️ Too Long\n(>120 min)'],
                        y=[valid, invalid, too_long],
                        marker=dict(
                            color=['#4caf50', '#f44336', '#ff9800'],
                            line=dict(color='white', width=2)
                        ),
                        text=[valid, invalid, too_long],
                        textposition='outside',
                        textfont=dict(size=14, family='Arial Black'),
                        hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
                    ),
                    row=2, col=3
                )
            
            # 7. MISSING DATA ANALYSIS
            missing_data = (self.df.isnull().sum() / len(self.df) * 100).sort_values(ascending=False).head(8)
            missing_data = missing_data[missing_data > 0]
            
            if len(missing_data) > 0:
                display_names = [col.split('/')[-1] if '/' in col else col for col in missing_data.index]
                
                fig.add_trace(
                    go.Bar(
                        y=display_names,
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
            quality_score = self._calculate_quality_score(duration_column, min_duration_threshold)
            
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
            
            # 10. PIVOTED BENEFICIARY TABLE (Districts as rows, Beneficiary/NotBeneficiary as columns)
            if treatment_column and treatment_column in self.df.columns and district_column and district_column in self.df.columns:
                beneficiary_pivot = self._create_beneficiary_pivot_table(
                    treatment_column, district_column
                )
                
                fig.add_trace(
                    go.Table(
                        header=dict(
                            values=list(beneficiary_pivot.keys()),
                            fill_color='#4facfe',
                            font=dict(color='white', size=14, family='Arial Black'),
                            align='center',
                            height=40
                        ),
                        cells=dict(
                            values=list(beneficiary_pivot.values()),
                            fill_color=[['#f0f4f8', '#ffffff'] * (len(beneficiary_pivot['District']) // 2)],
                            font=dict(color='#333', size=13),
                            align='center',
                            height=35
                        )
                    ),
                    row=5, col=1
                )
                logger.info("Added pivoted beneficiary table")
            
            # 11. ENUMERATOR PERFORMANCE TABLE WITH GPS AND DISTRICT
            if enumerator_column and enumerator_column in self.df.columns and duration_column in self.df.columns:
                enum_performance = self._calculate_enumerator_performance_detailed(
                    enumerator_column, duration_column, district_column, 
                    lat_column, lon_column, min_duration_threshold, max_duration_threshold
                )
                
                fig.add_trace(
                    go.Table(
                        header=dict(
                            values=list(enum_performance.keys()),
                            fill_color='#ff6b6b',
                            font=dict(color='white', size=12, family='Arial Black'),
                            align='center',
                            height=40
                        ),
                        cells=dict(
                            values=list(enum_performance.values()),
                            fill_color=[['#fff3f3', '#ffffff'] * (len(enum_performance['Enumerator']) // 2)],
                            font=dict(color='#333', size=11),
                            align='center',
                            height=30
                        )
                    ),
                    row=6, col=1
                )
                logger.info("Added detailed enumerator performance table with GPS and location")
            
            # Update layout
            fig.update_layout(
                height=2000,
                showlegend=False,
                title={
                    'text': f'<b>{title}</b><br><sup>Last Updated: {datetime.now().strftime("%B %d, %Y %H:%M:%S")} | ⚠️ Minimum Valid Duration: 50 minutes</sup>',
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
    
    def _create_beneficiary_pivot_table(self, treatment_col, district_col):
        """Create pivoted beneficiary table: Districts as rows, Beneficiary/NotBeneficiary as columns"""
        
        # Get target districts from config
        target_districts = self.config.get('target_districts', [
            'Bosaso', 'Dhusamareb', 'Beletweyne', 'Baki', 'Gabiley'
        ])
        
        # Create a readable treatment column
        self.df['Treatment_Label'] = self.df[treatment_col].apply(lambda x: 
            'Beneficiary' if str(x).lower() in ['1', 'yes', 'true', 'beneficiary', 'treatment'] 
            else 'NotBeneficiary' if str(x).lower() in ['0', 'no', 'false', 'non-beneficiary', 'control']
            else 'Unknown'
        )
        
        # Create pivot table
        pivot = pd.crosstab(
            self.df[district_col], 
            self.df['Treatment_Label'], 
            margins=False
        )
        
        # Ensure columns exist
        if 'Beneficiary' not in pivot.columns:
            pivot['Beneficiary'] = 0
        if 'NotBeneficiary' not in pivot.columns:
            pivot['NotBeneficiary'] = 0
        
        # Add all target districts (even if they have no data)
        for district in target_districts:
            if district not in pivot.index:
                pivot.loc[district] = 0
        
        # Select only Beneficiary and NotBeneficiary columns
        pivot = pivot[['Beneficiary', 'NotBeneficiary']]
        
        # Sort by target districts order
        pivot = pivot.reindex(target_districts, fill_value=0)
        
        # Add Grand Total column (row totals)
        pivot['Grand Total'] = pivot['Beneficiary'] + pivot['NotBeneficiary']
        
        # Add Grand Total row
        grand_total_row = pd.DataFrame({
            'Beneficiary': [pivot['Beneficiary'].sum()],
            'NotBeneficiary': [pivot['NotBeneficiary'].sum()],
            'Grand Total': [pivot['Grand Total'].sum()]
        }, index=['Grand Total'])
        
        pivot = pd.concat([pivot, grand_total_row])
        
        # Convert to dictionary for table
        table_data = {
            'District': list(pivot.index),
            'Beneficiary': list(pivot['Beneficiary'].astype(int)),
            'NotBeneficiary': list(pivot['NotBeneficiary'].astype(int)),
            'Grand Total': list(pivot['Grand Total'].astype(int))
        }
        
        return table_data
    
    def _calculate_enumerator_performance_detailed(self, enum_col, duration_col, district_col, 
                                                   lat_col, lon_col, min_duration, max_duration):
        """Calculate enumerator performance with GPS coordinates and district information"""
        
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
        
        # Get all enumerators
        enumerators = self.df[enum_col].value_counts().index
        
        for enum in enumerators:
            enum_data = self.df[self.df[enum_col] == enum]
            
            total = len(enum_data)
            too_short = enum_data['is_too_short'].sum() if 'is_too_short' in enum_data.columns else 0
            too_long = enum_data['is_too_long'].sum() if 'is_too_long' in enum_data.columns else 0
            avg_dur = enum_data[duration_col].mean()
            invalid_pct = (too_short / total * 100) if total > 0 else 0
            
            # Get districts where this enumerator worked
            if district_col and district_col in enum_data.columns:
                districts = enum_data[district_col].value_counts().to_dict()
                district_str = ', '.join([f"{dist}({cnt})" for dist, cnt in districts.items()])
            else:
                district_str = 'N/A'
            
            # Get GPS coordinates (show a few examples or range)
            if lat_col in enum_data.columns and lon_col in enum_data.columns:
                gps_data = enum_data[[lat_col, lon_col]].dropna()
                if len(gps_data) > 0:
                    # Show first 2 GPS coordinates as examples
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
            performance['Avg Duration'].append(f"{avg_dur:.1f}min")
            performance['Invalid %'].append(f"{invalid_pct:.1f}%")
        
        # Sort by number of invalid interviews (too short) descending
        sorted_indices = sorted(range(len(performance['❌ Too Short'])), 
                               key=lambda i: performance['❌ Too Short'][i], 
                               reverse=True)
        
        # Reorder all columns
        for key in performance:
            performance[key] = [performance[key][i] for i in sorted_indices]
        
        # Limit to top 15
        max_rows = 15
        for key in performance:
            performance[key] = performance[key][:max_rows]
        
        return performance
    
    def _calculate_completion_stats(self, district_col, duration_col, enum_col):
        """Calculate comprehensive completion statistics"""
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
        """Calculate overall data quality score"""
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
    dashboard = ONAQualityDashboard('ona_data_export.csv')
    if dashboard.load_data():
        dashboard.generate_dashboard()
