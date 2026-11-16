document.addEventListener("DOMContentLoaded", function () {

    // Confirm before deleting a website.
    document.querySelectorAll(".delete-form").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (!confirm("Are you sure you want to delete this website?")) {
                event.preventDefault();
            }
        });
    });

    // Confirm the new password fields match.
    const passwordForm = document.querySelector(
        'form[action*="/settings"], .form-card form'
    );

    const confirmPassword = document.getElementById("confirm_password");
    const newPassword = document.getElementById("new_password");

    if (passwordForm && confirmPassword && newPassword) {
        passwordForm.addEventListener("submit", function (event) {
            if (newPassword.value !== confirmPassword.value) {
                event.preventDefault();
                alert("New password and confirmation do not match.");
                confirmPassword.focus();
            }
        });
    }
});
