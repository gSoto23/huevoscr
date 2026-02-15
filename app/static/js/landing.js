function getLocation() {
    const btn = document.getElementById('geoBtn');
    const msg = document.getElementById('geoMsg');
    const input = document.getElementById('location_pin');

    if (!navigator.geolocation) {
        msg.textContent = "Geolocalización no soportada por su navegador.";
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Obteniendo...';
    msg.textContent = "";

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            const mapLink = `https://www.google.com/maps?q=${lat},${lng}`;
            input.value = mapLink;
            btn.innerHTML = '<i class="fa-solid fa-check"></i> Listo';
            btn.disabled = false;
        },
        (error) => {
            console.error(error);
            let errMsg = "Error obteniendo ubicación.";
            if (error.code === 1) errMsg = "Permiso denegado. Habilite la ubicación.";
            msg.textContent = errMsg;
            msg.style.color = "var(--color-red)";
            btn.innerHTML = '<i class="fa-solid fa-location-dot"></i> Reintentar';
            btn.disabled = false;
        }
    );
}

document.getElementById('subscriptionForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    const messageDiv = document.getElementById('formMessage');
    const btn = e.target.querySelector('button');

    btn.disabled = true;
    btn.textContent = 'Enviando...';
    messageDiv.classList.add('hidden');
    messageDiv.className = 'hidden'; // reset classes

    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    // Custom Validation
    // Auto-prepend 506 if exactly 8 digits
    if (/^\d{8}$/.test(data.whatsapp_id)) {
        data.whatsapp_id = '506' + data.whatsapp_id;
    }

    if (!/^\d{8,}$/.test(data.whatsapp_id)) {
        messageDiv.textContent = 'El número de WhatsApp debe tener al menos 8 dígitos.';
        messageDiv.className = 'error-message';
        messageDiv.classList.remove('hidden');
        btn.disabled = false;
        btn.textContent = 'Guardar Suscripción';
        return;
    }

    // Check other required fields (HTML required attribute catches empty, but checking whitespace doesn't hurt)
    if (!data.name.trim() || !data.address.trim()) {
        messageDiv.textContent = 'Por favor complete todos los campos requeridos.';
        messageDiv.className = 'error-message';
        messageDiv.classList.remove('hidden');
        btn.disabled = false;
        btn.textContent = 'Guardar Suscripción';
        return;
    }

    // Convert cartons_qty to int
    data.cartons_qty = parseInt(data.cartons_qty);

    // Sanitize optional fields: Pydantic EmailStr fails on empty string
    if (!data.email) delete data.email;
    if (!data.location_pin) delete data.location_pin;

    // Explicitly set is_active default for new users if needed, but backend handles it
    data.is_active = true; // This might be ignored by backend schema but harmless

    try {
        const response = await fetch('/customers/public', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            const result = await response.json();
            messageDiv.textContent = '¡Gracias! Tu información ha sido guardada exitosamente.';
            messageDiv.className = 'success-message';
            messageDiv.classList.remove('hidden');
        } else {
            const error = await response.json();
            messageDiv.textContent = 'Error: ' + (error.detail || 'Ocurrió un problema');
            messageDiv.className = 'error-message';
            messageDiv.classList.remove('hidden');
        }
    } catch (err) {
        messageDiv.textContent = 'Error de conexión. Intenta nuevamente.';
        messageDiv.className = 'error-message';
        messageDiv.classList.remove('hidden');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Guardar Suscripción';
    }
});

// Auto-fill logic could go here (if we want to fetch by WA ID on blur)
document.getElementById('whatsapp_id').addEventListener('blur', async function (e) {
    const waId = e.target.value;
    if (waId.length > 7) {
        // Option: we could fetch public info if we want to allow auto-fill
        // But for privacy, maybe we don't expose GET public without auth?
        // The requirements say "El sistema busca el registro -> Permite modificar".
        // Usually implies we need to fetch it.
        // Let's assume we can fetch basic data if we implement a public GET endpoint, 
        // OR we just rely on the backend "upsert".
        // Ideally, for "Edit", we need to show current values.
        // Let's implement a safe way to fetch later if needed.
    }
});
