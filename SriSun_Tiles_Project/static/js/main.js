document.addEventListener('DOMContentLoaded', function () {
    const alertList = document.querySelectorAll('.alert');
    alertList.forEach(function (alertNode) {
        setTimeout(function () {
            if (alertNode && alertNode.parentNode) {
                alertNode.classList.remove('show');
                alertNode.classList.add('fade');
                setTimeout(function () {
                    if (alertNode.parentNode) {
                        alertNode.remove();
                    }
                }, 300);
            }
        }, 4000);
    });
});
