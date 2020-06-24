

function goBack(){
	window.history.back()
}
function confirmDelete(){
	if(confirm("Are you sure to delete your review?"))
		return true
	else
		return false
}
function toggleForm(){
	var x = document.getElementById("overlay")
	var y = document.getElementById("addButton")
	var z = document.getElementById("rating")
	if(x.style.display == "block"){
		x.style.display = "none"
		y.style.display = "block"
		z.style.display = "block"
	}
	else{
		x.style.display = "block"
		y.style.display = "none"
		z.style.display ="none"
	}

}