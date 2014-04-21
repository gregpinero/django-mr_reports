Customizing a Report with Javascript
=============

The "Js post processing" field on the report screen is useful for many customizations
such as adding charts, grouping data, or formatting data.

(Tip: It's often easier to reference a CDN to bring in Javascript libraries rather than updating
your server.  This page has many popular JS libraries available: http://cdnjs.com/ )


Examples
--------------

Create bar chart (using High Charts) using first column for categories and second column for values::

    <script src="http://code.highcharts.com/highcharts.js"></script>
    <script>
    $(function () { 
        $('#cell_for_chart1').highcharts({
            chart: {
                type: 'bar'
            },
            title: {
                text: 'Popular Colors'
            },

          // These make it work nicely with wkhtmltopdf (required for PDF output)
          plotOptions: { series: { enableMouseTracking: false, shadow: false, animation: false } },

            xAxis: {
                categories:$('.data_table:first tbody tr td:first-child').map(function(i,val){
    return $(val).text();})
            },
            yAxis: {
                title: {
                    text: 'Number of Vehicles'
                }
            },
            series: [{
                name: '#Vehicles',
                data: $('.data_table:first tbody tr td:nth-child(2)').map(function(i,val){
    return parseInt($(val).text());})
            }]
        });
    });
    </script>



Format a table column to use commas in numbers::

    <script src="//cdnjs.cloudflare.com/ajax/libs/numeral.js/1.4.5/numeral.min.js"></script>
    <script>
    // Finding the 3rd column of the first data table and changing the value for a number with comma's
    // See more formatting options here: http://adamwdraper.github.io/Numeral-js/

    $('.data_table:first tbody tr td:nth-child(3)').each(function(i,val){
        $(val).html( numeral(val.innerHTML).format('0,0'));
    });
    </script>



Allow toggling of the 4th and 5th columns to show or hide::

    <script>
    var hidden_state = false;
    $('div.jumbotron .container').append('<a id="show_details">Show Details</a>');

    function toggle_details() {
         hidden_state = !hidden_state;
        if (hidden_state) {
            $('#show_details').html('Show Details');
        }
        else {
            $('#show_details').html('Hide Details');
        }
        $('.data_table:first tbody tr td:nth-child(4)').toggle();
        $('.data_table:first tbody tr td:nth-child(5)').toggle();
        $('.data_table:first thead tr th:nth-child(4)').toggle();
        $('.data_table:first thead tr th:nth-child(5)').toggle();
    }
    toggle_details();

    $('#show_details').click(function(){toggle_details();});
    </script>

