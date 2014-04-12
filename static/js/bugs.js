
$(document).ready(function() {
    $("#clr").click(function() {
        $("#q").val('').focus();
    });
    $("#q").focus();
    $('#q').keypress(function (e) {
        if (e.which == 13) {
            $('#formSearch').submit();
            return false;
        }
    });
});
